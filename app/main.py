from pathlib import Path
from statistics import mean
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from .db import init_db, connect
from .worker import start_scheduler, schedule_watch, unschedule_watch, check_watch
from .config import DEFAULT_INTERVAL

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app = FastAPI(title="PriceRadar", version="0.2.0")

CATEGORIES = ["home", "mobility", "food", "household", "workshop", "energy", "other"]
UNITS = ["piece", "kg", "g", "l", "ml", "m", "m2", "m3", "kwh", "hour", "pack"]


def _number(value: str):
    return float(value.replace(",", ".")) if value and value.strip() else None


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


@app.on_event("startup")
def startup():
    init_db()
    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "service": "priceradar", "version": "0.2.0"}


@app.get("/api/watches")
def api_watches():
    with connect() as con:
        rows = con.execute("SELECT * FROM watches ORDER BY id DESC").fetchall()
    return [_enrich(r) for r in rows]


@app.get("/api/watches/{watch_id}/history")
def api_history(watch_id: int):
    with connect() as con:
        rows = con.execute("SELECT price,currency,checked_at,source FROM price_history WHERE watch_id=? ORDER BY checked_at ASC", (watch_id,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/market")
def api_market():
    with connect() as con:
        rows = con.execute("SELECT * FROM watches WHERE last_price IS NOT NULL ORDER BY category,name").fetchall()
    groups = {}
    for row in rows:
        groups.setdefault(row["category"] or "other", []).append(_enrich(row))
    return {"categories": groups, "tracked_items": len(rows)}


@app.get("/api/market/index")
def api_market_index():
    with connect() as con:
        rows = con.execute("SELECT * FROM watches WHERE last_price IS NOT NULL").fetchall()
    category_values = {}
    for row in rows:
        with connect() as con:
            history = con.execute("SELECT price FROM price_history WHERE watch_id=? ORDER BY checked_at DESC LIMIT 30", (row["id"],)).fetchall()
        prices = [float(x["price"]) for x in history]
        if len(prices) >= 2 and prices[-1] > 0:
            category = row["category"] or "other"
            category_values.setdefault(category, []).append((prices[0] / prices[-1] - 1) * 100)
    return {"index_change_percent": {k: round(mean(v), 2) for k, v in category_values.items() if v}}


@app.get("/", response_class=HTMLResponse)
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
    })


@app.post("/watches")
def create_watch(
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
    check_watch(watch_id)
    return RedirectResponse("/", status_code=303)


@app.post("/watches/{watch_id}/check")
def manual_check(watch_id: int):
    check_watch(watch_id)
    return RedirectResponse("/", status_code=303)


@app.post("/watches/{watch_id}/toggle")
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


@app.post("/watches/{watch_id}/delete")
def delete_watch(watch_id: int):
    unschedule_watch(watch_id)
    with connect() as con:
        con.execute("DELETE FROM price_history WHERE watch_id=?", (watch_id,))
        con.execute("DELETE FROM watches WHERE id=?", (watch_id,))
    return RedirectResponse("/", status_code=303)
