import sqlite3
from contextlib import contextmanager
from .config import BASE_DIR, DB_PATH, DEFAULT_INTERVAL, SMART_POLLING_MAX_SECONDS, SMART_POLLING_MIN_SECONDS

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    selector TEXT,
    target_price REAL,
    currency TEXT DEFAULT 'EUR',
    interval_seconds INTEGER NOT NULL DEFAULT 86400,
    active INTEGER NOT NULL DEFAULT 1,
    category TEXT DEFAULT 'other',
    unit TEXT,
    pack_quantity REAL,
    consumption_per_month REAL,
    stock_quantity REAL,
    buy_below REAL,
    buy_when_days_left REAL,
    smart_polling INTEGER NOT NULL DEFAULT 1,
    polling_base_seconds INTEGER,
    polling_min_seconds INTEGER NOT NULL DEFAULT 3600,
    polling_max_seconds INTEGER NOT NULL DEFAULT 604800,
    last_price REAL,
    last_checked TEXT,
    last_status TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id INTEGER NOT NULL,
    price REAL NOT NULL,
    currency TEXT,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATIONS = {
    "category": "ALTER TABLE watches ADD COLUMN category TEXT DEFAULT 'other'",
    "unit": "ALTER TABLE watches ADD COLUMN unit TEXT",
    "pack_quantity": "ALTER TABLE watches ADD COLUMN pack_quantity REAL",
    "consumption_per_month": "ALTER TABLE watches ADD COLUMN consumption_per_month REAL",
    "stock_quantity": "ALTER TABLE watches ADD COLUMN stock_quantity REAL",
    "buy_below": "ALTER TABLE watches ADD COLUMN buy_below REAL",
    "buy_when_days_left": "ALTER TABLE watches ADD COLUMN buy_when_days_left REAL",
    "smart_polling": "ALTER TABLE watches ADD COLUMN smart_polling INTEGER NOT NULL DEFAULT 1",
    "polling_base_seconds": "ALTER TABLE watches ADD COLUMN polling_base_seconds INTEGER",
    "polling_min_seconds": "ALTER TABLE watches ADD COLUMN polling_min_seconds INTEGER NOT NULL DEFAULT 3600",
    "polling_max_seconds": "ALTER TABLE watches ADD COLUMN polling_max_seconds INTEGER NOT NULL DEFAULT 604800",
}


def init_db():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(SCHEMA)
        existing = {row[1] for row in con.execute("PRAGMA table_info(watches)")}
        for column, statement in MIGRATIONS.items():
            if column not in existing:
                con.execute(statement)
        con.execute(
            "UPDATE watches SET polling_base_seconds=COALESCE(polling_base_seconds, interval_seconds, ?), "
            "polling_min_seconds=COALESCE(polling_min_seconds, ?), "
            "polling_max_seconds=COALESCE(polling_max_seconds, ?)"
            , (DEFAULT_INTERVAL, SMART_POLLING_MIN_SECONDS, SMART_POLLING_MAX_SECONDS)
        )
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")


def get_setting(key: str, default=None):
    with connect() as con:
        row = con.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with connect() as con:
        con.execute(
            "INSERT INTO app_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (key, value),
        )


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()
