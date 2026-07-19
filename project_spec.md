# UK Stock Analyzer — Project Specification

## Product vision

A UK stock market analysis and screening system that combines technical analysis, fundamental data, news sentiment, machine learning pattern recognition, and LLM-assisted reasoning to surface high-probability trade candidates from the FTSE 100 and FTSE 250 each morning — without requiring manual stock suggestions from the user.

The system learns from every prediction and outcome over time, improving screening accuracy as more data is collected.

---

## Target user

**Profile:** Self-directed UK retail investor (non-professional developer as project owner).

| Attribute | Detail |
|-----------|--------|
| Broker | Interactive Investor (GBP settlement) |
| Universe | LSE-listed FTSE 100 and FTSE 250 only |
| Hold period | 2–8 weeks typically |
| Target gain | 8–15% per trade |
| Stop loss | ~7–8% below entry |
| Exit style | Full position exits (no partial sells) |
| Chart timeframes | Daily, weekly, monthly candlesticks |

### Entry criteria (user's trading style)

- Stock at or near support on daily chart (within ~3%)
- Not in confirmed downtrend on weekly timeframe
- Not at resistance on monthly timeframe
- Strong analyst consensus (buy-heavy)
- Specific dated catalyst within 4–8 weeks (results, trading update, etc.)
- Exit at identified resistance or analyst consensus price target

---

## Core goals

1. **Scan nightly** — Filter and analyse tradeable UK stocks; email aimed **before 07:00 UK**
2. **Multi-timeframe technical analysis** — Daily, weekly, monthly
3. **Fundamental + catalyst layer** — Analyst consensus, upside %, upcoming dated events
4. **Morning shortlist** — 5–10 candidates with **company name**, score, and **why chosen**
5. **Learn over time** — Shadow log, 2/4/8-week outcomes, ML after enough labels
6. **Coaching loop** — User writes analysis → honest AI critique (correct / wrong / risks)
7. **Fast cloud UI** — FastAPI + HTMX (not Streamlit); TradingView charts

---

## Stock universe filters

Reduce ~350 FTSE constituents to ~120–150 before analysis:

| # | Filter |
|---|--------|
| 1 | LSE primary listing only (exclude dual-listed foreign stocks, e.g. Kinnevik, Hexagon) |
| 2 | Minimum average daily volume: 500,000 shares |
| 3 | Minimum market cap: £300 million |
| 4 | Minimum analyst coverage: 4+ analysts |
| 5 | Exclude investment trusts and REITs |
| 6 | Positive or improving free cash flow trajectory |
| 7 | All prices in GBP pence (GBX) regardless of reporting currency |

---

## Key features by phase

### Phase 0 — Data validation
- Validate yfinance LSE price data (GBp/GBP consistency)
- Currency normalisation and quarantine logic
- Cross-check suspicious tickers via Finnhub free tier

### Phase 1 — Core pipeline
- Universe build and filters 1–3
- Daily OHLCV ingestion (2+ years history)
- pandas-ta indicators on daily / weekly / monthly
- SQLite database

### Phase 2 — Fundamentals and news
- Finnhub analyst data (targets, ratings)
- RNS and RSS news ingestion
- Sentiment scoring (VADER + FinBERT locally; optional API upgrade)
- Catalyst date extraction (regex on RNS; LLM fallback for ambiguous items)

### Phase 3 — Scoring and shadow logging
- Composite score with explicit configurable weights
- Multi-timeframe confluence scoring (0–3)
- Auto-log top 15 nightly candidates with full feature snapshot
- Walk-forward backtest on rule set

### Phase 4 — User observations
- Log observations (buy / watch / avoid, confidence, chart description)
- Automated 2 / 4 / 8-week outcome tracking
- Pattern performance statistics

### Phase 5 — Machine learning
- scikit-learn models after 100+ shadow outcomes
- Walk-forward cross-validation (never random shuffle)
- Feature importance display
- Embedding-based pattern matching (sentence-transformers)

### Phase 6 — Dashboard and automation (v1, legacy)
- Streamlit prototype (superseded in rebuild v2)

### Rebuild v2 — Product surface
- FastAPI + HTMX web app (Render/Railway)
- Why-chosen explanations + coaching critique
- TradingView Lightweight Charts
- Reliable single weekday cron + email by ~07:00 UK

---

## Dashboard views (v2)

### 1. Shortlist
Name, ticker, score, support distance, timeframes, conflict, ML prob; link to detail with why-chosen.

### 2. Stock detail
Chart, why shortlisted, score breakdown, your analysis, coach critique, external research links.

### 3. Holdings
II CSV import, P&L vs cost (Yahoo/scan prices).

### 4. Notes / coaching
Saved analyses and critiques.

### 5. ML status
Outcomes N/100, model meta, shadow hit rates, feature importance in plain English.

---

## Learning system (how accuracy improves)

**Yes — the system becomes more useful the more you use it**, but with important caveats:

| Mechanism | What improves | When it helps |
|-----------|---------------|---------------|
| Shadow logging | Unbiased training data from every nightly scan | From day 1 |
| Outcome tracking | Labels for 2/4/8-week gain/loss and stop hits | After 2+ weeks |
| Pattern statistics | Hit rates per setup type (e.g. "support bounce + catalyst") | After ~30 observations per pattern |
| ML model | Probability of 8%+ gain within 8 weeks | After 100+ labelled outcomes |
| Chart description embeddings | Match new setups to your past language and results | After ~20 logged descriptions |
| Composite weight tuning | Backtest-driven weight adjustments | Ongoing |

**What does NOT automatically improve:**
- Raw price data quality (requires validation layer, not usage)
- Analyst data freshness (requires scheduled refresh)
- LLM/news accuracy (requires good sources + optional paid API for critical paths)

**Honest expectation:** Months 1–3 rely on rules and composite scoring. ML predictions appear only after sufficient labelled data. Pattern stats are anecdotal below ~30 samples per type.

---

## Non-goals

- Not financial advice — all output is analytical, not "you should buy"
- No automatic Interactive Investor integration (no public API)
- No intraday / day-trading signals
- No US or non-UK markets in v1
- No paid data subscriptions (Bloomberg, LSEG Workspace) in v1

---

## Cost philosophy

**Target: £0/month infrastructure.** Quality is not sacrificed on data libraries or indicators — only on optional prose generation.

| Priority | Approach |
|----------|----------|
| Data accuracy | Finnhub validation, GBX normalisation, quarantine — non-negotiable |
| Technical analysis | pandas-ta, pandas — industry standard, free |
| ML | scikit-learn locally — free |
| Hosting | GitHub Actions + Render/Railway + Supabase — free/cheap |
| LLM | Haiku for morning prose + coaching critique; usage tracked |

---

## Success criteria (v2)

- [ ] Weekday email most days before 07:00 UK
- [ ] One full pipeline per weekday
- [ ] FastAPI app usable on phone; chart zoom works
- [ ] Shortlist shows name + why chosen + catalysts
- [ ] External link opens correct instrument ≥90% for shortlist
- [ ] Coaching critique stored beside user analysis
- [ ] ML status clear on one screen
- [ ] System runs when local PC is off (GitHub Actions)

---

## Glossary

| Term | Meaning |
|------|---------|
| GBX / GBp | UK stock prices in pence (100 pence = £1) |
| RNS | Regulatory News Service (LSE official announcements) |
| Confluence score | 0–3 count of bullish-aligned timeframes (daily, weekly, monthly) |
| Shadow log | Automatic feature snapshot of top candidates without user action |
| Catalyst | Dated event (results, AGM, ex-dividend, trading update) |
| Composite score | Weighted combination of technical, fundamental, catalyst, and sentiment factors |
