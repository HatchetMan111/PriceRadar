from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from .db import connect
from .scraper import check_url
from .notify import send_notifications

scheduler = BackgroundScheduler(daemon=True)

def _now(): return datetime.now(timezone.utc).isoformat()

def check_watch(watch_id: int):
    with connect() as con: row = con.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
    if not row or not row["active"]: return
    try:
        result = check_url(row["url"], row["selector"]); previous = row["last_price"]
        now = _now()
        with connect() as con:
            con.execute("UPDATE watches SET last_price=?, last_checked=?, last_status='ok', last_error=NULL WHERE id=?", (result.price, now, watch_id))
            con.execute("INSERT INTO price_history(watch_id,price,currency,checked_at,source) VALUES(?,?,?,?,?)", (watch_id,result.price,result.currency,now,result.source))
        messages=[]
        if row["target_price"] is not None and result.price <= row["target_price"] and (previous is None or previous > row["target_price"]):
            messages.append(f"🎯 {row['name']} is at {result.price:.2f} {result.currency} (target {row['target_price']:.2f})\n{row['url']}")
        if previous is not None and result.price < previous:
            drop=(previous-result.price)/previous*100
            if drop >= 1: messages.append(f"📉 {row['name']} dropped {drop:.1f}% to {result.price:.2f} {result.currency}\n{row['url']}")
        for msg in messages: send_notifications(msg)
    except Exception as exc:
        with connect() as con: con.execute("UPDATE watches SET last_checked=?, last_status='error', last_error=? WHERE id=?", (_now(),str(exc)[:1000],watch_id))

def schedule_watch(watch_id:int, interval_seconds:int):
    scheduler.add_job(check_watch,"interval",seconds=interval_seconds,args=[watch_id],id=f"watch-{watch_id}",replace_existing=True,max_instances=1,coalesce=True)

def unschedule_watch(watch_id:int):
    try: scheduler.remove_job(f"watch-{watch_id}")
    except Exception: pass

def start_scheduler():
    if not scheduler.running: scheduler.start()
    with connect() as con: rows=con.execute("SELECT id,interval_seconds FROM watches WHERE active=1").fetchall()
    for row in rows: schedule_watch(row["id"],row["interval_seconds"])
