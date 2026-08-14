from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from .db import init_db, connect
from .worker import start_scheduler, schedule_watch, unschedule_watch, check_watch
from .config import DEFAULT_INTERVAL
BASE=Path(__file__).parent
templates=Jinja2Templates(directory=str(BASE/"templates"))
app=FastAPI(title="PriceRadar",version="0.1.0")
@app.on_event("startup")
def startup(): init_db(); start_scheduler()
@app.get("/health")
def health(): return {"status":"ok","service":"priceradar"}
@app.get("/api/watches")
def api_watches():
    with connect() as con: rows=con.execute("SELECT * FROM watches ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]
@app.get("/api/watches/{watch_id}/history")
def api_history(watch_id:int):
    with connect() as con: rows=con.execute("SELECT price,currency,checked_at,source FROM price_history WHERE watch_id=? ORDER BY checked_at ASC",(watch_id,)).fetchall()
    return [dict(r) for r in rows]
@app.get("/",response_class=HTMLResponse)
def dashboard(request:Request):
    with connect() as con:
        watches=con.execute("SELECT w.*,(SELECT MIN(price) FROM price_history p WHERE p.watch_id=w.id) AS lowest_price,(SELECT COUNT(*) FROM price_history p WHERE p.watch_id=w.id) AS checks FROM watches w ORDER BY w.id DESC").fetchall()
    return templates.TemplateResponse("index.html",{"request":request,"watches":watches,"default_interval":DEFAULT_INTERVAL})
@app.post("/watches")
def create_watch(name:str=Form(...),url:str=Form(...),selector:str=Form(""),target_price:str=Form(""),interval_seconds:int=Form(DEFAULT_INTERVAL)):
    target=float(target_price.replace(",",".")) if target_price.strip() else None; interval=max(300,min(interval_seconds,7*86400))
    with connect() as con:
        cur=con.execute("INSERT INTO watches(name,url,selector,target_price,interval_seconds) VALUES(?,?,?,?,?)",(name.strip(),url.strip(),selector.strip() or None,target,interval)); watch_id=cur.lastrowid
    schedule_watch(watch_id,interval); check_watch(watch_id); return RedirectResponse("/",status_code=303)
@app.post("/watches/{watch_id}/check")
def manual_check(watch_id:int): check_watch(watch_id); return RedirectResponse("/",status_code=303)
@app.post("/watches/{watch_id}/toggle")
def toggle_watch(watch_id:int):
    with connect() as con:
        row=con.execute("SELECT active,interval_seconds FROM watches WHERE id=?",(watch_id,)).fetchone()
        if not row: return JSONResponse({"error":"not found"},status_code=404)
        active=0 if row["active"] else 1; con.execute("UPDATE watches SET active=? WHERE id=?",(active,watch_id))
    if active: schedule_watch(watch_id,row["interval_seconds"])
    else: unschedule_watch(watch_id)
    return RedirectResponse("/",status_code=303)
@app.post("/watches/{watch_id}/delete")
def delete_watch(watch_id:int):
    unschedule_watch(watch_id)
    with connect() as con:
        con.execute("DELETE FROM price_history WHERE watch_id=?",(watch_id,)); con.execute("DELETE FROM watches WHERE id=?",(watch_id,))
    return RedirectResponse("/",status_code=303)
