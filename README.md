# 🛰️ PriceRadar

**PriceRadar is a self-hosted personal price memory for Proxmox VE.** It watches arbitrary price sources and turns them into a long-term record of what things cost in *your* world.

The goal is bigger than a traditional price comparison site: track the things you know you will need again — fuel, LPG, heating oil, local petrol stations, food, building materials, household consumables, car supplies and anything else with a usable price source.

## Install on Proxmox

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/HatchetMan111/PriceRadar/main/ct/priceradar.sh)"
```

The installer creates an unprivileged Debian LXC, installs PriceRadar as a systemd service and prints the web UI address.

### Login

The installer generates a random HTTP Basic Auth password on first install and prints it at the end (also saved in `/etc/priceradar.env` on the LXC, readable by root and the `priceradar` service user only):

```text
Login       : admin / <generated password>
              (stored in /etc/priceradar.env - change it any time)
```

Change it at any time by editing `/etc/priceradar.env` and running `systemctl restart priceradar`. If you remove `PRICERADAR_AUTH_USER` / `PRICERADAR_AUTH_PASSWORD` entirely, the app falls back to **no authentication** (a warning is logged on startup) — not recommended for anything reachable beyond localhost.

## The four-layer architecture

PriceRadar is deliberately organized into four layers. The first three are deterministic and useful without AI; the fourth adds intelligence on top of trustworthy structured data.

### 1. Monitor — What does it cost now?

Watch prices from:

- arbitrary product pages
- JavaScript-rendered pages (browser fetcher planned)
- JSON-LD / Schema.org
- CSS selectors and structured attributes
- local retailer websites
- supermarket offers and PDFs (planned)
- APIs and imported data (planned)
- manual price entries/imports for suppliers with no useful website (planned)

Each watch stores the source, current price, currency, status and polling interval.

### 2. History — What did it cost before?

PriceRadar builds a personal price history:

- lowest observed price
- price changes
- historical averages
- trends
- category-level personal price index
- unusual price detection (planned)

The important concept is **your observed local market**, not a claim to know the entire market.

### 3. Consumption — When will I need it?

A watch can optionally contain:

- unit (`l`, `kg`, `m2`, `piece`, ...)
- pack quantity
- monthly consumption
- current stock
- a price threshold
- a number of remaining days at which buying should start

Example:

> Flüssiggas: 420 L in stock, ~125 L/month consumption, buy when ≤ 30 days remain.

PriceRadar can then show:

- 🟢 **JETZT KAUFEN**
- 🟡 **BALD KAUFEN**
- 🔵 **BEOBACHTEN**

This turns a price tracker into a personal purchasing calendar.

### 4. Intelligence — When should I buy?

The long-term intelligence layer will combine price, trend, stock and consumption into useful decisions:

- Buy Windows
- price anomaly detection
- best time to refill fuel/LPG/heating oil
- personal price index
- recurring purchase forecasts
- basket optimization across shops
- cheapest price per kg/L/m²/piece
- product equivalence / matching
- local-market summaries

### Local AI is optional

AI is **not required** for the core scraper. It should be used where semantics are hard, not for every HTTP request.

Good future AI jobs:

1. Find the relevant price when a page contains many numbers.
2. Normalize product names (`Nutella 750g`, `Nutella Nuss-Nougat-Creme 0.75kg`).
3. Match equivalent products between retailers.
4. Understand units and pack sizes.
5. Explain anomalies and trends.
6. Answer questions over the user's own price/consumption history.

The architecture should remain deterministic-first:

```text
URL / source
    ↓
Fetcher
    ↓
Deterministic extractor
    ↓
Normalized price record
    ↓
History + consumption
    ↓
Buy Window / alerts
    ↓
Optional local AI
```

## Examples

### Fuel

Track your preferred local petrol stations and compare the current price with your personal history.

> Super E10: 1.649 €/L — 4.0 ct/L below your normal observed price.

### LPG / heating oil

Track a supplier or public quote page and combine price with your expected consumption.

> LPG: 0.73 €/L · 420 L stock · ~125 L/month · ~103 days remaining.

### Food

Track package sizes and later normalize them to comparable units:

```text
750 g Nutella → 5.49 € → 7.32 €/kg
450 g Nutella → 3.79 € → 8.42 €/kg
1 kg Nutella  → 6.99 € → 6.99 €/kg
```

### Building materials

Track OSB, insulation, drywall, timber, paint, cement, screws and other materials that are poorly covered by traditional price portals.

> OSB 2500×675×18 mm → 14.99 € → 8.88 €/m²

## Personal Market vision

After months of observations, PriceRadar can become a personal market database:

```text
MY MARKET
──────────────
Home         ↓ 4.1%
Mobility     ↑ 1.2%
Food         ↓ 1.7%
Household    ↓ 3.4%
Workshop     ↑ 2.1%

4 items: good time to buy
7 items: monitor
2 items: likely needed soon
```

Future versions can add a personal annual cost forecast based on historical consumption and observed prices.

## Current MVP features

- Any product URL
- CSS selector or automatic price extraction
- JSON-LD / structured attributes / common selectors / text fallback
- SQLite price history
- Per-watch polling intervals
- Target-price and price-drop alerts
- ntfy and generic webhook notifications
- categories
- consumption and stock tracking
- Buy Window calculation
- personal market API
- dashboard and health endpoint
- one-line Proxmox LXC installation

## Scraping policy

PriceRadar is a polite monitor. It respects `robots.txt` by default (and fails **closed** — i.e. refuses to fetch — if `robots.txt` can't be reached at all, rather than assuming permission), uses a configurable User-Agent and minimum request delay, and does **not** bypass CAPTCHAs, authentication, paywalls, bot challenges or access controls.

A browser fetcher for JavaScript-heavy pages is planned. Browser rendering does not guarantee that a site will permit automated access.

## Security

PriceRadar fetches whatever URL you give it, on a schedule, from a server on your network — so it's built with deliberate guardrails:

- **SSRF protection**: every watch URL (and every redirect hop it follows) is resolved and checked; requests to loopback, private/RFC1918, link-local and other reserved ranges are refused. Only `http`/`https` are allowed.
- **Response limits**: responses over `PRICERADAR_MAX_RESPONSE_BYTES` (default 5 MB) are rejected.
- **HTTP Basic Auth** protects the dashboard and API by default on a fresh install. `/health` stays open for uptime checks.
- Watch creation/checks run as background tasks, so a slow target site cannot tie up the web server.

Relevant environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `PRICERADAR_AUTH_USER` / `PRICERADAR_AUTH_PASSWORD` | HTTP Basic Auth credentials. Unset = no auth (logged as a warning). | unset |
| `PRICERADAR_RESPECT_ROBOTS` | Honor `robots.txt` | `true` |
| `PRICERADAR_MAX_RESPONSE_BYTES` | Max bytes read per fetch | `5242880` (5 MB) |
| `PRICERADAR_MAX_REDIRECTS` | Max redirect hops followed per fetch | `5` |
| `PRICERADAR_REQUEST_TIMEOUT` | Per-request timeout (seconds) | `30` |
| `PRICERADAR_MIN_REQUEST_DELAY` | Delay before each fetch (seconds) | `2` |

Known limitation: the SSRF check re-validates on every redirect hop, which closes the common redirect-based bypass, but it does not fully defend against DNS-rebinding. Full protection would require transport-level IP pinning.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and details.

## Roadmap

- [x] Generic URL monitoring
- [x] Price history
- [x] Target-price alerts
- [x] Personal categories
- [x] Consumption / stock model
- [x] Buy Window MVP
- [x] Security hardening
- [ ] Playwright browser fetcher
- [ ] Unit-price normalization (€/kg, €/L, €/m², ...)
- [ ] PDF/prospectus extraction
- [ ] Import/API providers
- [ ] Local petrol-station providers
- [ ] Product matching
- [ ] Personal price index
- [ ] Basket optimizer
- [ ] Optional local AI layer
- [ ] Home Assistant integration

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
