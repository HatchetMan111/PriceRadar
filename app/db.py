import sqlite3
from contextlib import contextmanager
from .config import DB_PATH, BASE_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    selector TEXT,
    target_price REAL,
    currency TEXT DEFAULT 'EUR',
    interval_seconds INTEGER NOT NULL DEFAULT 3600,
    active INTEGER NOT NULL DEFAULT 1,
    category TEXT DEFAULT 'other',
    unit TEXT,
    pack_quantity REAL,
    consumption_per_month REAL,
    stock_quantity REAL,
    buy_below REAL,
    buy_when_days_left REAL,
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
"""

MIGRATIONS = {
    "category": "ALTER TABLE watches ADD COLUMN category TEXT DEFAULT 'other'",
    "unit": "ALTER TABLE watches ADD COLUMN unit TEXT",
    "pack_quantity": "ALTER TABLE watches ADD COLUMN pack_quantity REAL",
    "consumption_per_month": "ALTER TABLE watches ADD COLUMN consumption_per_month REAL",
    "stock_quantity": "ALTER TABLE watches ADD COLUMN stock_quantity REAL",
    "buy_below": "ALTER TABLE watches ADD COLUMN buy_below REAL",
    "buy_when_days_left": "ALTER TABLE watches ADD COLUMN buy_when_days_left REAL",
}


def init_db():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(SCHEMA)
        existing = {row[1] for row in con.execute("PRAGMA table_info(watches)")}
        for column, statement in MIGRATIONS.items():
            if column not in existing:
                con.execute(statement)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")


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
