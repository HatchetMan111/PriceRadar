# PriceRadar

Self-hosted price monitoring for Proxmox VE. Track prices from arbitrary web pages, including products that do not appear in traditional price-comparison portals.

## MVP
- Any product URL
- CSS selector or automatic price extraction
- JSON-LD / structured attributes / common selectors / text fallback
- SQLite price history
- Per-watch polling intervals
- Target-price and price-drop alerts
- ntfy and generic webhook notifications
- Dashboard, manual checks and health endpoint

## One-line Proxmox install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/PriceRadar/main/ct/priceradar.sh)"
```

The installer creates an unprivileged Debian LXC and runs PriceRadar as a systemd service.

## AI

AI is intentionally not required for the MVP. Deterministic extraction is cheaper, faster and reproducible. A future optional AI layer can help with difficult JavaScript pages, semantic price selection, product matching and unit normalization. It should be a fallback, not a dependency for every request.

## Scraping

PriceRadar is a polite monitor. It respects robots.txt by default, uses a configurable User-Agent and minimum delay, and does not bypass CAPTCHAs, authentication, paywalls or access controls.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
