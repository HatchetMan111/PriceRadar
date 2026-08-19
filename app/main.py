import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .auth import auth_enabled, require_auth
from .config import DEFAULT_INTERVAL
from .db import connect, get_setting, init_db, set_setting
from .ollama import get_config as get_ollama_config, list_models, test_connection
from .worker import check_watch, schedule_watch, start_scheduler, unschedule_watch

logger = logging.getLogger("priceradar")
BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    start_scheduler()
    if not auth_enabled():
        logger.warning(
            "PRICERADAR_AUTH_USER / PRICERADAR_AUTH_PASSWORD are not set - "
            "the web UI and API are running WITHOUT authentication. Anyone "
            "who can reach this host on the network can add/delete watches "
            "and trigger outbound requests. Set both env vars to enable "
            "HTTP Basic Auth."
        )
    yield


app = FastAPI(title="PriceRadar", version="0.4.1", lifespan=lifespan)
protected = APIRouter(dependencies=[Depends(require_auth)])

CATEGORIES = ["home", "mobility", "food", "household", "workshop", "energy", "other"]
UNITS = ["piece", "kg", "g", "l", "ml", "m", "m2", "m3", "kwh", "hour", "pack"]
_NUMBER_STRIP = re.compile(r"[^\d,.\-]")


def _number(value: str):
    if not value or not value.strip():
        return None
    cleaned = _NUMBER_STRIP.sub("", value.strip())
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _buy_state(w):
    price = w["last_price"]
    if price is None:
        return "unknown"
    if w["buy_below"] is not None and price <= w["buy_below"]:
        return "buy"
    if w["stock_quantity"] is not None and w["consumption_per_month"] and w["consumption_per_month"] > 0:
        months_left = w["stock_quantity"] / w["consumption_per_month"]
        days_left = months_left * 30.4375
        if w["buy_when_days_left"] is not None and days_left <= w["buy_when_days_left"]:
            return "buy"
        if days_left <= 30:
            return "soon"
    return "watch"


def _enrich(w):
    data = dict(w)
    data["buy_state"] = _buy_state(w)
    if w["stock_quantity"] is not None and w["consumption_per_month"]:
        data["days_left"] = round(w["stock_quantity"] / w["consumption_per_month"] * 30.4375, 1)
    else:
        data["days_left"] = None
    return data


def _ollama_view():
    config = get_ollama_config()
    return {
        "enabled": config["enabled"],
        "url": config["url"],
        "model": config["model"],
        "source": "database" if get_setting("ollama.url") or get_setting("ollama.model") or get_setting("ollama.enabled") else "environment",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "priceradar", "version": "0.4.1", "auth_enabled": auth_enabled()}


@protected.get("/api/watches")
def api_watches():
    with connect() as con:
        rows = con.execute("SELECT * FROM watches ORDER BY id DESC").fetchall()
    return [_enrich(r) for r in rows]


@protected.get("/api/watches/{watch_id}/history")
def api_history(watch_id: int):
    with connect() as con:
        rows = con.execute("SELECT price,currency,checked_at,source FROM price_history WHERE watch_id=? ORDER BY checked_at ASC", (watch_id,)).fetchall()
    return [dict(r) for r in rows]


@protected.get("/api/market")
def api_market():
    with connect() as con:
        rows = con.execute("SELECT * FROM watches WHERE last_price IS NOT NULL ORDER BY category,name").fetchall()
    groups = {}
    for row in rows:
        groups.setdefault(row["category"] or "other", []).append(_enrich(row))
    return {"categories": groups, "tracked_items": len(rows)}


@protected.get("/api/market/index")
def api_market_index():
    category_values = {}
    with connect() as con:
        rows = con.execute("SELECT * FROM watches WHERE last_price IS NOT NULL").fetchall()
        for row in rows:
            history = con.execute(
                "SELECT price FROM price_history WHERE watch_id=? ORDER BY checked_at DESC LIMIT 30",
                (row["id"],),
            ).fetchall()
            prices = [float(x["price"]) for x in history]
            if len(prices) >= 2 and prices[-1] > 0:
                category = row["category"] or "other"
                category_values.setdefault(category, []).append((prices[0] / prices[-1] - 1) * 100)
    return {"index_change_percent": {k: round(mean(v), 2) for k, v in category_values.items() if v}}


@protected.get("/api/ollama/models")
def api_ollama_models():
    try:
        return {"ok": True, "models": list_models()}
    except (httpx.HTTPError, ValueError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@protected.post("/api/ollama/test")
def api_ollama_test(url: str = Form("")):
    try:
        return test_connection(url.strip() or None)
    except (httpx.HTTPError, ValueError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@protected.post("/settings/ollama")
def save_ollama_settings(
    background_tasks: BackgroundTasks,
    enabled: str = Form(""),
    url: str = Form(...),
    model: str = Form(...),
):
    url = url.strip().rstrip("/")
    model = model.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return RedirectResponse("/?settings_error=invalid_url", status_code=303)
    set_setting("ollama.enabled", "true" if enabled else "false")
    set_setting("ollama.url", url)
    set_setting("ollama.model", model or "qwen2.5:3b")
    return RedirectResponse("/?settings_saved=1", status_code=303)


@protected.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    with connect() as con:
        watches = con.execute("SELECT w.*,(SELECT MIN(price) FROM price_history p WHERE p.watch_id=w.id) AS lowest_price,(SELECT COUNT(*) FROM price_history p WHERE p.watch_id=w.id) AS checks FROM watches w ORDER BY category,w.id DESC").fetchall()
    enriched = [_enrich(w) for w in watches]
    buy_count = sum(w["buy_state"] == "buy" for w in enriched)
    soon_count = sum(w["buy_state"] == "soon" for w in enriched)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "watches": enriched,
        "default_interval": DEFAULT_INTERVAL,
        "categories": CATEGORIES,
        "units": UNITS,
        "buy_count": buy_count,
        "soon_count": soon_count,
        "ollama": _ollama_view(),
        "settings_saved": request.query_params.get("settings_saved") == "1",
        "settings_error": request.query_params.get("settings_error"),
    })


@protected.post("/watches")
def create_watch(
    background_tasks: BackgroundTasks,
    name: str = Form(...), url: str = Form(...), selector: str = Form(""), target_price: str = Form(""),
    interval_seconds: int = Form(DEFAULT_INTERVAL), category: str = Form("other"), unit: str = Form(""),
    pack_quantity: str = Form(""), consumption_per_month: str = Form(""), stock_quantity: str = Form(""),
    buy_below: str = Form(""), buy_when_days_left: str = Form(""),
):
    target = _number(target_price)
    interval = max(300, min(interval_seconds, 7 * 86400))
    category = category if category in CATEGORIES else "other"
    with connect() as con:
        cur = con.execute(
            "INSERT INTO watches(name,url,selector,target_price,interval_seconds,category,unit,pack_quantity,consumption_per_month,stock_quantity,buy_below,buy_when_days_left) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (name.strip(), url.strip(), selector.strip() or None, target, interval, category, unit.strip() or None,
             _number(pack_quantity), _number(consumption_per_month), _number(stock_quantity), _number(buy_below), _number(buy_when_days_left)),
        )
        watch_id = cur.lastrowid
    schedule_watch(watch_id, interval)
    background_tasks.add_task(check_watch, watch_id)
    return RedirectResponse("/", status_code=303)


@protected.post("/watches/{watch_id}/check")
def manual_check(watch_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(check_watch, watch_id)
    return RedirectResponse("/", status_code=303)


@protected.post("/watches/{watch_id}/toggle")
def toggle_watch(watch_id: int):
    with connect() as con:
        row = con.execute("SELECT active,interval_seconds FROM watches WHERE id=?", (watch_id,)).fetchone()
        if not row:
            return JSONResponse({"error": "not found"}, status_code=404)
        active = 0 if row["active"] else 1
        con.execute("UPDATE watches SET active=? WHERE id=?", (active, watch_id))
    if active:
        schedule_watch(watch_id, row["interval_seconds"])
    else:
        unschedule_watch(watch_id)
    return RedirectResponse("/", status_code=303)


@protected.post("/watches/{watch_id}/delete")
def delete_watch(watch_id: int):
    unschedule_watch(watch_id)
    with connect() as con:
        con.execute("DELETE FROM price_history WHERE watch_id=?", (watch_id,))
        con.execute("DELETE FROM watches WHERE id=?", (watch_id,))
    return RedirectResponse("/", status_code=303)


app.include_router(protected)
