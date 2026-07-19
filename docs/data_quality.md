# Data Quality & Sources (v2)

## Source of truth

| Field | Source | Notes |
|-------|--------|-------|
| OHLCV charts & Latest (p) | **yfinance** (Yahoo) | Normalised to GBX (pence) |
| Analyst targets | yfinance | Cached ~7 days |
| News / catalysts | RSS + heuristics | Not exhaustive RNS |
| Company name | yfinance / stocks table | Shown next to ticker |
| External research link | Yahoo Finance quote URL; Investing.com if slug mapped | |

**Investing.com is not the price feed.** Closes and charts can differ from Yahoo due to adjustments, delays, and venue differences. Always show a disclaimer on chart pages.

## Ticker normalisation

| II / display | Yahoo symbol | Notes |
|--------------|--------------|-------|
| BT.A | BT-A.L | Dot → hyphen for Yahoo |
| JD. | JD.L | Strip trailing epic dot |
| TW. | TW.L | Strip trailing epic dot |
| SHEL | SHEL.L | Append .L |

Canonical storage: Yahoo-style `.L` symbol. Display may show LSE epic without `.L`.

## Investing.com links

Do **not** use `/search/?q=...` as the only link (forces a chooser list).

1. Look up `data/investing_slugs.json` (or DB map)
2. If found → `https://www.investing.com/equities/{slug}`
3. Else → Yahoo Finance: `https://uk.finance.yahoo.com/quote/{YAHOO_TICKER}`

## Universe filters (hard gates)

| # | Rule | Default |
|---|------|---------|
| 1 | LSE `.L` only + exclusions.csv | — |
| 2 | Min avg volume | 500,000 |
| 3 | Min market cap GBP | 300,000,000 |
| 4 | Min analysts | 4 |
| 5 | Exclude trusts / REITs | — |
| 6 | Reject negative FCF when known | — |

### Quality feel (v2 tuning)

Shortlist can still include FTSE 250 names that feel “lower tier.” Optional penalties:

- Very high 20d volatility
- Barely-passing liquidity
- Weak multi-timeframe confluence with conflict flag

Document weight changes in `docs/decisions.md` when tuned.

## Tiered scanning

| Tier | Meaning | Recheck |
|------|---------|---------|
| active | Passes filters | Daily |
| watch | Near miss | ~7 days |
| cold | Far fail | ~30 days |

Always daily: II holdings + latest shadow top 15.

## GBX rules

- Yahoo `GBp` / `GBX` → already pence
- Yahoo `GBP` pounds → ×100 to pence
- Store and display as pence unless labelled otherwise

## Quarantine

Flags in `data_quality_flags`: stale prices, absurd jumps, pipeline errors. Quarantined tickers skip scoring for that day.
