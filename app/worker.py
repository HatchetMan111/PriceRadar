from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from .config import (
    SMART_POLLING_CHANGE_MULTIPLIER,
    SMART_POLLING_ENABLED,
    SMART_POLLING_MAX_SECONDS,
    SMART_POLLING_MIN_SECONDS,
    SMART_POLLING_STABLE_MULTIPLIER,
)
from .db import connect
from .notify import send_notifications
from .scraper import check_url

scheduler = BackgroundScheduler(daemon=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _next_interval(row, price_changed: bool) -> int:
    """Choose the next interval from the current interval.

    Stable prices back off toward the configured maximum. A change makes the
    watcher temporarily more active, down to its configured minimum. This
    keeps daily/weekly goods cheap to monitor while reacting faster to active
    prices such as fuel or electricity.
    """
    current = int(row["interval_seconds"] or row["polling_base_seconds"] or SMART_POLLING_MIN_SECONDS)
    minimum = int(row["polling_min_seconds"] or SMART_POLLING_MIN_SECONDS)
    maximum = int(row["polling_max_seconds"] or SMART_POLLING_MAX_SECONDS)
    if not SMART_POLLING_ENABLED or not row["smart_polling"]:
        return max(minimum, min(maximum, current))
    if price_changed:
        return max(minimum, min(maximum, int(current * SMART_POLLING_CHANGE_MULTIPLIER)))
    return max(minimum, min(maximum, int(current * SMART_POLLING_STABLE_MULTIPLIER)))


def check_watch(watch_id: int):
    with connect() as con:
        row = con.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
    if not row or not row["active"]:
        return

    try:
        result = check_url(row["url"], row["selector"])
        previous = row["last_price"]
        changed = previous is not None and abs(float(result.price) - float(previous)) > 1e-9
        now = _now()
        next_interval = _next_interval(row, changed)

        with connect() as con:
            con.execute(
                "UPDATE watches SET last_price=?, last_checked=?, last_status='ok', last_error=NULL, interval_seconds=? WHERE id=?",
                (result.price, now, next_interval, watch_id),
            )
            con.execute(
                "INSERT INTO price_history(watch_id,price,currency,checked_at,source) VALUES(?,?,?,?,?)",
                (watch_id, result.price, result.currency, now, result.source),
            )

        messages = []
        if row["target_price"] is not None and result.price <= row["target_price"] and (previous is None or previous > row["target_price"]):
            messages.append(
                f"🎯 {row['name']} is at {result.price:.2f} {result.currency} (target {row['target_price']:.2f})\n{row['url']}"
            )
        if previous is not None and result.price < previous:
            drop = (previous - result.price) / previous * 100
            if drop >= 1:
                messages.append(f"📉 {row['name']} dropped {drop:.1f}% to {result.price:.2f} {result.currency}\n{row['url']}")
        for msg in messages:
            send_notifications(msg)

        # Replace the scheduled job with the newly selected interval.
        schedule_watch(watch_id, next_interval)
    except Exception as exc:
        with connect() as con:
            con.execute(
                "UPDATE watches SET last_checked=?, last_status='error', last_error=? WHERE id=?",
                (_now(), str(exc)[:1000], watch_id),
            )
        # Errors should not create a tight retry loop.
        schedule_watch(watch_id, max(int(row["polling_min_seconds"] or SMART_POLLING_MIN_SECONDS), int(row["interval_seconds"] or SMART_POLLING_MIN_SECONDS)))


def schedule_watch(watch_id: int, interval_seconds: int):
    scheduler.add_job(
        check_watch,
        "interval",
        seconds=max(60, int(interval_seconds)),
        args=[watch_id],
        id=f"watch-{watch_id}",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def unschedule_watch(watch_id: int):
    try:
        scheduler.remove_job(f"watch-{watch_id}")
    except Exception:
        pass


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    with connect() as con:
        rows = con.execute("SELECT id,interval_seconds FROM watches WHERE active=1").fetchall()
    for row in rows:
        schedule_watch(row["id"], row["interval_seconds"])
