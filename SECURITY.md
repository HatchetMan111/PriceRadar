# Security

Please report security vulnerabilities privately to the maintainer rather than in public issues.

PriceRadar intentionally does not implement CAPTCHA bypassing, authentication bypassing, stealth/evasion techniques, credential scraping, proxy rotation for evasion, or other mechanisms intended to defeat access controls.

## Implemented protections

- **SSRF**: watch URLs and every redirect hop are validated against loopback/private/link-local/reserved IP ranges before being fetched; only `http`/`https` are accepted. See `app/scraper.py::_validate_url`.
- **Authentication**: HTTP Basic Auth via `PRICERADAR_AUTH_USER` / `PRICERADAR_AUTH_PASSWORD`, enabled by default on a fresh install (the installer generates a random password). `/health` is intentionally unauthenticated for uptime checks.
- **CSRF**: not implemented as a separate token scheme. Because auth is HTTP Basic rather than cookie/session-based, browsers do not attach stored credentials to cross-origin form submissions, which gives the mutating routes meaningful CSRF resistance.
- **Resource limits**: fetched responses are capped at `PRICERADAR_MAX_RESPONSE_BYTES` (default 5 MB); watch checks run as background tasks so a slow/hanging target cannot block the web server.
- **robots.txt**: fetched through the same SSRF-validated client and treated as fail-closed when it cannot be reached, rather than silently allowing the scrape.

## Known limitations

- The SSRF check does not fully defend against DNS-rebinding attacks (DNS record changed between our check and the underlying connection). Redirect-based bypasses are covered; full protection would require transport-level IP pinning.
- HTTP Basic Auth sends credentials on every request; run PriceRadar behind HTTPS if it is reachable outside a trusted LAN.
- PriceRadar is designed for a single trusted user/household. It has no per-user accounts, roles, or audit log.
