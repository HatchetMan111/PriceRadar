# 🛰️ PriceRadar

Self-hosted personal price monitoring for Proxmox VE. Track prices from arbitrary web pages and build a long-term personal price history for things you actually need: fuel, heating oil, LPG, food, building materials, household supplies and more.

## Core architecture

PriceRadar is organized into four layers:

1. **Monitor** — websites, APIs, PDFs and other price sources.
2. **History** — price history, lows, averages and trends.
3. **Consumption** — stock, monthly consumption and purchase cycles.
4. **Intelligence** — buy windows, anomalies, product normalization and optional local AI.

## Extraction pipeline

```text
URL
 ↓
SSRF + robots policy
 ↓
HTTP fetch
 ↓
JSON-LD / CSS / structured price extraction
 ↓
if no reliable price
 ↓
Playwright / Chromium for JavaScript-rendered pages
 ↓
if still unresolved
 ↓
optional local Ollama extraction
 ↓
price history + alerts + buy-window logic
```

Ollama is not required. Deterministic extraction is always preferred because it is faster, cheaper and reproducible.

## Connect an existing Ollama instance

PriceRadar does **not** need Ollama installed in the same LXC. You can point it at an existing instance from the web UI:

**Dashboard → 🦙 Lokale KI / Ollama**

Example Proxmox layout:

```text
Proxmox
├── LXC 100  PriceRadar   192.168.178.100
├── LXC 101  Ollama       192.168.178.101
└── LXC 102  Home Assistant
```

Set:

```text
Ollama URL: http://192.168.178.101:11434
Model:      qwen2.5:3b
Enabled:    yes
```

Then use **Verbindung testen** or **Modelle laden**. PriceRadar discovers models through Ollama's `/api/tags` endpoint.

The settings are persisted in SQLite, so they survive restarts and LXC reboots. Environment variables are still supported for unattended deployments:

```bash
PRICERADAR_OLLAMA_ENABLED=true
PRICERADAR_OLLAMA_URL=http://192.168.178.101:11434
PRICERADAR_OLLAMA_MODEL=qwen2.5:3b
```

The Ollama URL must be an absolute `http://` or `https://` URL and must not contain embedded credentials.

## One-line Proxmox install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/PriceRadar/main/ct/priceradar.sh)"
```

The installer creates an unprivileged Debian LXC, installs PriceRadar as a systemd service and optionally installs Chromium for browser fallback.

## Requirements

- Proxmox VE 8+
- Internet access from the Proxmox host and LXC
- Default allocation: 2 CPU cores / 2 GiB RAM / 8 GiB disk

## Polite scraping

PriceRadar is a monitor, not a bypass tool. It does not attempt to bypass CAPTCHAs, bot challenges, authentication, paywalls or access controls. `robots.txt` is respected by default. Use a reasonable interval and only disable the robots policy when you have the right to access the source that way.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:8080`.

## Roadmap

- Grundpreise: €/kg, €/L, €/m² and €/piece
- More PDF/OCR price sources
- Product matching and normalization
- Personal price index
- Smart buy windows based on price + consumption + inventory
- Basket optimization
- More local source/provider adapters
