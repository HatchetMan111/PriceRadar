# PriceRadar Architecture

## Product model

PriceRadar treats every tracked item as a **personal market observation** rather than merely a URL.

A watch can represent:

- a product (Nutella, OSB)
- a consumable (washing detergent, coffee)
- an energy commodity (LPG, heating oil)
- a local price point (petrol station)
- a service or recurring cost

The long-term data model is:

```text
Source
  ↓
Observation
  ↓
Normalized Product / Commodity
  ↓
Price History
  ↓
Consumption + Stock
  ↓
Buy Window
  ↓
Personal Market Intelligence
```

## Four layers

### 1. Monitor

Fetch and extract a price from a source. Deterministic extraction comes first.

Planned providers include HTTP, browser rendering, PDF/OCR, APIs and manual/import sources.

### 2. History

Persist every observation. The system can calculate lowest price, rolling averages, trend and anomalies from its own history.

### 3. Consumption

Optional user context makes a price actionable. For example:

```text
LPG
stock: 420 L
consumption: 125 L/month
price: 0.73 €/L
```

This gives an estimated remaining supply of about 103 days.

### 4. Intelligence

The intelligence layer should consume structured observations, not replace the scraper.

Examples:

- buy-window scoring
- anomaly detection
- recurring purchase prediction
- product matching
- unit normalization
- basket optimization
- natural-language questions over local history

## AI design principle

AI is optional. The system must remain useful when no model is installed.

Use deterministic methods for:

- HTTP fetching
- JSON-LD extraction
- CSS/XPath selection
- numeric parsing
- unit arithmetic
- historical calculations
- alert thresholds

Use local AI only for semantic tasks such as:

- choosing a price from ambiguous page content
- mapping product names to a canonical product
- understanding pack sizes
- explaining a price anomaly
- answering questions about the user's own historical data

This keeps cost, latency and failure modes under control.

## Personal Market

A future personal market index should be based on the user's own tracked basket and optionally weighted by consumption.

Example weighting concept:

```text
annual_cost_weight = expected_annual_quantity × observed_unit_price
```

This allows the dashboard to distinguish a 20% change in a rarely purchased item from a 5% change in a major annual expense such as fuel.

The index must clearly state that it represents the user's tracked observations, not an official consumer price index.

## Source/provider model

The architecture should eventually support provider adapters:

```text
providers/
  generic_web
  browser
  pdf
  api
  petrol_station
  supermarket
  heating_fuel
  manual
```

Provider adapters return a common observation object. The rest of PriceRadar should not care whether a price came from HTML, an API, a PDF or a manual import.

## Safety and reliability

PriceRadar should not bypass access controls. It may use normal browser rendering for JavaScript-heavy pages, but must not circumvent CAPTCHAs, authentication, paywalls or bot challenges.

Every extracted price should eventually carry a confidence/source field. AI-derived observations should be marked as such and should be reviewable by the user.
