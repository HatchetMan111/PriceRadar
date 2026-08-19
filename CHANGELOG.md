# Changelog

## 0.4.1

### Added
- Web UI settings for a local or remote Ollama instance.
- Persisted Ollama URL, enabled flag and selected model in SQLite.
- Connection test from the PriceRadar settings page.
- Automatic Ollama model discovery via `/api/tags`.
- Remote Ollama support for another Proxmox LXC, GPU host or LAN server.
- Ollama URL validation requiring `http://` or `https://` and rejecting embedded credentials.
- Environment variables remain supported as defaults for unattended deployments.

### Design
- Ollama remains optional and is only used as an extraction fallback.
- PriceRadar does not require Ollama to be installed in the PriceRadar LXC.
- The same local Ollama instance can be shared by multiple self-hosted services.

## 0.4.0

### Added
- HTTP → deterministic extraction → Playwright/Chromium → optional Ollama extraction pipeline.
- Adaptive smart polling with per-watch minimum/maximum intervals.
- Optional Chromium installation for JavaScript-rendered pages.
- Local Ollama extraction fallback with confidence checking.
- Documentation and tests for the browser/Ollama/smart-polling pipeline.

## 0.3.0

### Added
- Personal market model with categories, units, stock and consumption.
- Buy-window states based on target prices and remaining stock.
- Personal market API and category index.
- SSRF protections and HTTP Basic Auth.
