import os
from pathlib import Path

BASE_DIR = Path(os.getenv("PRICERADAR_DATA_DIR", "/var/lib/priceradar"))
DB_PATH = BASE_DIR / "priceradar.db"
USER_AGENT = os.getenv("PRICERADAR_USER_AGENT", "PriceRadar/0.1 (+self-hosted price monitor)")
DEFAULT_INTERVAL = int(os.getenv("PRICERADAR_DEFAULT_INTERVAL", "3600"))
REQUEST_TIMEOUT = float(os.getenv("PRICERADAR_REQUEST_TIMEOUT", "30"))
MIN_REQUEST_DELAY = float(os.getenv("PRICERADAR_MIN_REQUEST_DELAY", "2"))
RESPECT_ROBOTS = os.getenv("PRICERADAR_RESPECT_ROBOTS", "true").lower() in {"1", "true", "yes", "on"}

# Optional local Ollama extraction. Disabled by default.
OLLAMA_ENABLED = os.getenv("PRICERADAR_OLLAMA_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
OLLAMA_URL = os.getenv("PRICERADAR_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("PRICERADAR_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = float(os.getenv("PRICERADAR_OLLAMA_TIMEOUT", "60"))
OLLAMA_MAX_TEXT_CHARS = int(os.getenv("PRICERADAR_OLLAMA_MAX_TEXT_CHARS", "24000"))

# HTTP Basic Auth. If either value is unset, the app runs without authentication
# (not recommended; startup logs a warning in that case).
AUTH_USER = os.getenv("PRICERADAR_AUTH_USER") or None
AUTH_PASSWORD = os.getenv("PRICERADAR_AUTH_PASSWORD") or None

# SSRF hardening for the scraper (see app/scraper.py).
ALLOWED_SCHEMES = {"http", "https"}
MAX_RESPONSE_BYTES = int(os.getenv("PRICERADAR_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))
MAX_REDIRECTS = int(os.getenv("PRICERADAR_MAX_REDIRECTS", "5"))
