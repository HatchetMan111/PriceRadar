import os
from pathlib import Path

BASE_DIR = Path(os.getenv("PRICERADAR_DATA_DIR", "/var/lib/priceradar"))
DB_PATH = BASE_DIR / "priceradar.db"
USER_AGENT = os.getenv("PRICERADAR_USER_AGENT", "PriceRadar/0.2 (+self-hosted price monitor)")
DEFAULT_INTERVAL = int(os.getenv("PRICERADAR_DEFAULT_INTERVAL", "86400"))
REQUEST_TIMEOUT = float(os.getenv("PRICERADAR_REQUEST_TIMEOUT", "30"))
MIN_REQUEST_DELAY = float(os.getenv("PRICERADAR_MIN_REQUEST_DELAY", "2"))
RESPECT_ROBOTS = os.getenv("PRICERADAR_RESPECT_ROBOTS", "true").lower() in {"1", "true", "yes", "on"}

# Optional local Ollama extraction. Disabled by default.
OLLAMA_ENABLED = os.getenv("PRICERADAR_OLLAMA_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
OLLAMA_URL = os.getenv("PRICERADAR_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("PRICERADAR_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = float(os.getenv("PRICERADAR_OLLAMA_TIMEOUT", "60"))
OLLAMA_MAX_TEXT_CHARS = int(os.getenv("PRICERADAR_OLLAMA_MAX_TEXT_CHARS", "24000"))

# Optional Chromium/Playwright fallback for JavaScript-rendered pages.
BROWSER_ENABLED = os.getenv("PRICERADAR_BROWSER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
BROWSER_TIMEOUT = float(os.getenv("PRICERADAR_BROWSER_TIMEOUT", "45"))

# Adaptive polling. The scheduler starts with each watch's configured interval,
# then backs off when a price remains stable and becomes more frequent after a
# change. Per-watch limits are stored in the database.
SMART_POLLING_ENABLED = os.getenv("PRICERADAR_SMART_POLLING_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SMART_POLLING_MIN_SECONDS = int(os.getenv("PRICERADAR_SMART_POLLING_MIN_SECONDS", "3600"))
SMART_POLLING_MAX_SECONDS = int(os.getenv("PRICERADAR_SMART_POLLING_MAX_SECONDS", str(7 * 86400)))
SMART_POLLING_STABLE_MULTIPLIER = float(os.getenv("PRICERADAR_SMART_POLLING_STABLE_MULTIPLIER", "2"))
SMART_POLLING_CHANGE_MULTIPLIER = float(os.getenv("PRICERADAR_SMART_POLLING_CHANGE_MULTIPLIER", "0.5"))

# HTTP Basic Auth. If either value is unset, the app runs without authentication
# (not recommended; startup logs a warning in that case).
AUTH_USER = os.getenv("PRICERADAR_AUTH_USER") or None
AUTH_PASSWORD = os.getenv("PRICERADAR_AUTH_PASSWORD") or None

# SSRF hardening for the scraper (see app/scraper.py).
ALLOWED_SCHEMES = {"http", "https"}
MAX_RESPONSE_BYTES = int(os.getenv("PRICERADAR_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))
MAX_REDIRECTS = int(os.getenv("PRICERADAR_MAX_REDIRECTS", "5"))
