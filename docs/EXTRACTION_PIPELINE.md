# Extraction pipeline

PriceRadar uses a layered extraction strategy so the normal path stays fast, local and deterministic.

```text
URL
 ↓
SSRF validation + robots.txt
 ↓
HTTP fetch
 ↓
JSON-LD / CSS / attributes / regex
 │
 ├─ price found → save
 │
 └─ no price
       ↓
   Playwright/Chromium
       ↓
   render JavaScript
       ↓
   same deterministic extractor
       │
       ├─ price found → save
       │
       └─ no price
             ↓
        local Ollama (optional)
             ↓
           save / error
```

## Why this order?

- HTTP is cheap and works for many shops.
- Browser rendering handles JavaScript-generated prices without making an LLM part of every request.
- Ollama is an optional fallback for semantic extraction from difficult pages.
- No external AI API is required.

## robots.txt and access controls

The browser and Ollama layers do **not** bypass `robots.txt`, authentication, CAPTCHAs or other access controls. If PriceRadar cannot legally/technically fetch a page, an LLM cannot make the missing page content appear.

If a site explicitly permits your monitoring, the administrator can make an informed decision about `PRICERADAR_RESPECT_ROBOTS=false`. This is not an anti-blocking feature.

## Ollama

Enable it with:

```text
PRICERADAR_OLLAMA_ENABLED=true
PRICERADAR_OLLAMA_URL=http://ollama:11434
PRICERADAR_OLLAMA_MODEL=qwen2.5:3b
```

Ollama receives cleaned page text only after deterministic extraction fails. Its result is treated as untrusted data and must contain a valid positive price and sufficient confidence before it is accepted.

## Browser mode

Browser mode is enabled by default in the full installer. It can be disabled with:

```text
PRICERADAR_BROWSER_ENABLED=false
```

The installer places Chromium in `/opt/priceradar/browsers` and the systemd service exposes that path through `PLAYWRIGHT_BROWSERS_PATH`.

## Smart polling

Every watch can adapt its interval:

- unchanged price → back off toward the maximum interval
- changed price → poll faster toward the minimum interval
- default minimum: 1 hour
- default maximum: 7 days
- default multiplier on stability: 2x
- default multiplier after a change: 0.5x

This makes daily price checks cheap for stable products while allowing volatile prices such as fuel or electricity to react faster.

The feature can be disabled globally with `PRICERADAR_SMART_POLLING_ENABLED=false` and is stored per watch for future UI controls.
