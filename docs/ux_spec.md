# UX Specification (v2)

## Principles

- Mobile-first; few clicks to chart
- Plain English; no trader jargon (no “MTF”)
- Every shortlisted stock: **name + ticker + why chosen**
- Honest coaching — never flattery
- Loading states that explain wait (never endless spinner without text)

## Screens

### Home `/`

- Latest scan date/time, last email status, next expected run
- Anthropic usage this month
- ML status one-liner (active / N of 100 outcomes)
- Nav: Shortlist, Holdings, Portfolio/Notes, ML, Lookup

### Shortlist `/shortlist`

Table columns: Rank | Name | Ticker | Score | Support dist % | Timeframes | Conflict | ML prob 8%+

Each row expands or links to detail.

### Stock detail `/stock/{ticker}`

1. Header: **Company name (TICKER.L)** + external links (Yahoo preferred; Investing.com if mapped)
2. **Why shortlisted** card (bullets from `why_chosen`)
3. Chart (TradingView Lightweight Charts) — Daily / Weekly / Monthly
4. Price source caption: Yahoo Finance via yfinance; may differ from Investing.com
5. Score breakdown table
6. **Your analysis** form → submit
7. **Coach critique** panel (after request)

### Holdings `/holdings`

- Upload II holdings CSV (not transaction history preferred)
- One results table (no duplicate preview table after import)
- Blank latest → “Awaiting scan” or live fallback label

### Portfolio / notes `/notes`

- List of analyses + critiques
- Filter by ticker / awaiting critique

### ML `/ml`

- Outcomes labelled N/100
- Model version, trained_at, CV score
- Shadow hit rates 2w/4w/8w
- Feature importance in plain English
- Explicit “not predicting yet” when inactive

### Login

- Shared `APP_PASSWORD` cookie/session

## Coaching loop

1. User reads why_chosen + chart
2. User writes: thesis, what they see on chart, agree/disagree with system
3. System calls Haiku with strict prompt:
   - Correct because…
   - Wrong or weak because…
   - What could happen…
   - No praise without substance; challenge confirmation bias
4. Store notes + critique; allow revise

## Chart behaviour

- Candlestick + volume
- Pinch/drag zoom on mobile; mouse wheel/drag on desktop
- Timeframe toggle does not reload whole page painfully
- Max ~2 years daily points (downsample weekly/monthly as needed)

## Email

- Subject clear; company **name + ticker** in table
- Why-chosen bullets or link to app detail
- Terminology matches app
