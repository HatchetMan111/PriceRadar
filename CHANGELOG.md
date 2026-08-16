# Changelog

## 0.3.0 — Security hardening

**Security fixes**

- **SSRF**: watch URLs are now resolved and checked against loopback/private/link-local/reserved IP ranges before fetching, and again on every redirect hop (closes the redirect-based bypass). Only `http`/`https` schemes are allowed. `robots.txt` fetches go through the same validated path (previously bypassed it entirely).
- **No authentication**: added optional HTTP Basic Auth (`PRICERADAR_AUTH_USER` / `PRICERADAR_AUTH_PASSWORD`), enabled by default on fresh installs via a randomly generated password. `/health` stays open. A startup warning is logged if auth is left unconfigured.
- **robots.txt fail-open**: a failed lookup now denies the fetch instead of silently allowing it.
- **DoS via blocking fetch**: watch creation/checks now run as background tasks instead of blocking the HTTP request on an outbound fetch.
- **Unbounded response size**: fetched pages are capped at `PRICERADAR_MAX_RESPONSE_BYTES` (default 5 MB).
- **Command injection risk** in the installers: `PRICERADAR_REPO_URL` is validated and passed as a separate environment argument instead of being interpolated into shell text.

**Bug fixes**

- `_number()` now handles European and English thousands/decimal formats plus currency symbols and units, returning `None` for invalid optional input instead of raising.
- `GET /api/market/index` now reuses one SQLite connection instead of opening one per watch.
- Replaced deprecated FastAPI startup events with a lifespan handler.

**Docs**

- Documented generated login credentials, security environment variables, scraper guardrails and known limitations.
- Added `SECURITY.md` guidance.

**Tests**

- Added SSRF validation tests and robust number parsing tests.
