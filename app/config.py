import os
from pathlib import Path

BASE_DIR = Path(os.getenv("PRICERADAR_DATA_DIR", "/var/lib/priceradar"))
DB_PATH = BASE_DIR / "priceradar.db"
USER_AGENT = os.getenv("PRICERADAR_USER_AGENT", "PriceRadar/0.1 (+self-hosted price monitor)")
DEFAULT_INTERVAL = int(os.getenv("PRICERADAR_DEFAULT_INTERVAL", "3600"))
REQUEST_TIMEOUT = float(os.getenv("PRICERADAR_REQUEST_TIMEOUT", "30"))
MIN_REQUEST_DELAY = float(os.getenv("PRICERADAR_MIN_REQUEST_DELAY", "2"))
RESPECT_ROBOTS = os.getenv("PRICERADAR_RESPECT_ROBOTS", "true").lower() in {"1", "true", "yes", "on"}
