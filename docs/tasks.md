# Development Roadmap

Structured task list broken into small, completable items. Work top-to-bottom within each phase.

**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done

---

## Foundation

### Repository and environment

- [x] Create `project_spec.md`
- [x] Create `docs/architecture.md`
- [x] Create `docs/decisions.md`
- [x] Create `docs/progress.md`
- [x] Create `docs/tasks.md`
- [x] Create `.cursor/rules`
- [ ] Create private GitHub repository
- [ ] Initial git commit and push
- [ ] Create `requirements.txt` with pinned core dependencies
- [ ] Create `pyproject.toml` or minimal package config
- [ ] Create `.env.example` (FINNHUB_API_KEY, optional ANTHROPIC_API_KEY, DATABASE_URL)
- [ ] Create `.gitignore`
- [ ] Create `README.md` with setup instructions
- [ ] Create Python virtual environment and verify install

### Project scaffold

- [ ] Create `src/` package structure (see architecture.md)
- [ ] Create `config/config.yaml` with composite score weights
- [ ] Create `data/` directory (gitignored db files)
- [ ] Create `logs/` directory (gitignored)
- [ ] Create `reports/` directory
- [ ] Create `scripts/run_nightly.py` stub
- [ ] Create `app/streamlit_app.py` stub
- [ ] Create `tests/` directory with `conftest.py`

---

## Phase 0 — Data validation

**Goal:** Prove yfinance LSE data is usable with <2% error rate on test set.

- [ ] Create list of 30 representative `.L` tickers (large cap, mid cap, commodities, financials)
- [ ] Build `src/data/prices.py` — basic yfinance fetch
- [ ] Log `meta.currency` for each ticker
- [ ] Build GBX normalisation function (handle GBp, GBX, GBP edge cases)
- [ ] Build sanity checks: >25% daily jump, zero volume, stale date
- [ ] Cross-check suspicious tickers against Finnhub quote endpoint
- [ ] Build quarantine list mechanism (`data_quality_flags` table)
- [ ] Document failure rate in `docs/phase0_report.md`
- [ ] Write pytest tests for normalisation (known good/bad examples)
- [ ] **Exit:** <2% discrepancies on 30-ticker test set

---

## Phase 1 — Core pipeline

**Goal:** Nightly job produces indicator table for full filtered universe.

### Database

- [ ] Write `src/db/schema.sql` (all tables from architecture.md)
- [ ] Build `src/db/connection.py` (SQLite local, Supabase URL for cloud)
- [ ] Build `src/db/repositories.py` — CRUD helpers
- [ ] Migration/initialise script

### Universe

- [ ] Build FTSE 100 + FTSE 250 constituent list fetcher
- [ ] Create `data/exclusions.csv` (dual-listed stocks, trusts, REITs)
- [ ] Implement filters 1–3: listing, volume ≥500k, market cap ≥£300m
- [ ] Store filtered universe in `stocks` table

### Price ingestion

- [ ] Batch fetch 2 years daily OHLCV for universe
- [ ] Apply GBX normalisation and quarantine
- [ ] Upsert into `daily_prices`
- [ ] Handle missing data gracefully (log, don't crash)

### Technical analysis

- [ ] Resample daily → weekly → monthly OHLCV
- [ ] Calculate SMA 20/50/200 per timeframe
- [ ] Calculate RSI 14, MACD, OBV per timeframe
- [ ] Detect golden/death cross (50 vs 200 SMA)
- [ ] Store in `technical_indicators` table

### Pipeline orchestration

- [ ] Build `src/pipeline/nightly.py` — steps 1–5 (universe, prices, indicators)
- [ ] Build `scripts/run_nightly.py` CLI
- [ ] Add structured logging
- [ ] Record `scan_runs` metadata
- [ ] **Exit:** `python scripts/run_nightly.py` completes for full universe

---

## Phase 2 — Fundamentals and news

**Goal:** Candidates show analyst upside and catalyst dates.

### Fundamentals (Finnhub)

- [ ] Register Finnhub free API key
- [ ] Build `src/data/fundamentals.py` — recommendations, price targets, profile
- [ ] Implement filter 4: minimum 4 analysts
- [ ] Implement filter 5: exclude trusts/REITs (sector field + exclusion list)
- [ ] Implement filter 6: FCF trajectory check (best effort from Finnhub financials)
- [ ] Cache analyst data 7 days; refresh on earnings weeks
- [ ] Store in `analyst_data` table

### News and RNS

- [ ] Build `src/data/news.py` — RSS feed parser (Reuters UK, RNS, FT, Proactive)
- [ ] Map article text to universe tickers (ticker regex + company name map)
- [ ] Filter noise categories (own shares, voting rights, PDMR)
- [ ] Store in `news_items` table

### Sentiment

- [ ] Build `src/intelligence/sentiment.py` — VADER on headlines
- [ ] Add FinBERT scoring for flagged articles (optional batch, CPU)
- [ ] Cache sentiment by article URL hash (24h)

### Catalysts

- [ ] Build `src/intelligence/catalysts.py` — regex date extraction from RNS
- [ ] Parse event types: results, AGM, ex-dividend, trading update
- [ ] Flag catalysts within 6 weeks
- [ ] Store in `catalysts` table
- [ ] **Exit:** Each universe stock has analyst data and catalyst scan

---

## Phase 3 — Scoring and shadow logging

**Goal:** Ranked candidate list + backtest report.

### Support and resistance

- [ ] Build `src/analysis/support_resistance.py`
- [ ] Pivot point calculation
- [ ] Fractal-based S/R (2+ reversals in 12 months)
- [ ] Distance from nearest support/resistance as %

### Scoring

- [ ] Build `src/analysis/scoring.py` — composite score from config weights
- [ ] Multi-timeframe confluence score (0–3)
- [ ] Conflict flag (daily buy vs weekly/monthly sell)
- [ ] Market regime: FTSE 100 vs 50-day MA
- [ ] Sector relative strength (4-week return vs sector)
- [ ] Snapshot weights in `config_snapshots`

### Shadow logging

- [ ] Auto-log top 15 candidates to `candidates` table nightly
- [ ] Store full feature vector per candidate

### Backtesting

- [ ] Build `scripts/run_backtest.py`
- [ ] Walk-forward backtest: support + catalyst + confluence ≥2 entry rules
- [ ] Exit rules: +8% target, -7.5% stop, 8-week max hold
- [ ] Output report to `reports/backtest_YYYY-MM-DD.md`
- [ ] **Exit:** Ranked list of 5–10 candidates with backtest summary

---

## Phase 4 — User observations

**Goal:** User can log trades; outcomes auto-track at 2/4/8 weeks.

### Observation logging

- [ ] Build observation form in Streamlit
- [ ] Fields: ticker, entry price, buy/watch/avoid, confidence, chart description
- [ ] Snapshot all technical indicators at log time
- [ ] Parse chart description via keyword map → structured JSON

### Outcome tracking

- [ ] Build `src/pipeline/outcomes.py`
- [ ] For each observation: price at 2, 4, 8 weeks
- [ ] Calculate % gain/loss
- [ ] Flag target hit and stop hit
- [ ] Mark correct/incorrect vs prediction
- [ ] Store in `outcomes` table

### Pattern statistics

- [ ] Calculate rolling hit rate per pattern type
- [ ] Store in `pattern_stats` table
- [ ] **Exit:** Log observation → auto outcomes after 2 weeks

---

## Phase 5 — Machine learning

**Goal:** ML predictions shown when n ≥ 100 labelled outcomes.

### Embeddings

- [ ] Build `src/intelligence/patterns.py`
- [ ] Embed chart descriptions with sentence-transformers
- [ ] Cosine similarity search against historical observations
- [ ] Template display: "Similar pattern: 10/14 wins, avg +9.1%"

### ML model

- [ ] Build `src/intelligence/ml_model.py`
- [ ] Feature matrix from observations + shadow logs
- [ ] Walk-forward cross-validation
- [ ] Logistic regression at 100+ samples
- [ ] Random Forest at 300+ samples
- [ ] Store model artifact and metadata in `model_versions`
- [ ] Feature importance chart for Streamlit
- [ ] Display "insufficient data" below threshold
- [ ] **Exit:** ML probability shown on morning scan when ready

---

## Phase 6 — Dashboard and cloud deployment

**Goal:** Dashboard live on Streamlit Cloud; pipeline runs via GitHub Actions.

### Streamlit dashboard

- [ ] `app/streamlit_app.py` — home page with latest scan summary
- [ ] `pages/1_morning_scan.py` — ranked candidates, expanders, Plotly charts
- [ ] `pages/2_portfolio.py` — open observations, P&L, alerts
- [ ] `pages/3_patterns.py` — hit rates, feature importance
- [ ] `pages/4_lookup.py` — ad-hoc ticker lookup
- [ ] Connect to Supabase in cloud, SQLite locally

### Morning report

- [ ] Build `src/reports/morning_report.py` — Jinja2 HTML template
- [ ] Output to `reports/morning_YYYY-MM-DD.html`

### GitHub Actions

- [ ] Create `.github/workflows/nightly.yml` — cron 17:30 UK weekdays
- [ ] Configure secrets: FINNHUB_API_KEY, DATABASE_URL, optional ANTHROPIC_API_KEY
- [ ] Fail notification on workflow error

### Supabase setup

- [ ] Create Supabase free project
- [ ] Run schema migration
- [ ] Configure DATABASE_URL in GitHub secrets and Streamlit Cloud

### Streamlit Community Cloud

- [ ] Connect GitHub repo to Streamlit Cloud
- [ ] Configure secrets (DATABASE_URL)
- [ ] Deploy `app/streamlit_app.py`
- [ ] **Exit:** Open dashboard on phone; pipeline ran overnight without local PC

### Optional upgrades

- [ ] Add Anthropic Haiku for morning prose summaries
- [ ] Gmail SMTP morning email digest
- [ ] Interactive Investor CSV import

---

## Task sizing guide

| Size | Effort | Example |
|------|--------|---------|
| S | <2 hours | Add config field, single pytest |
| M | 2–6 hours | One module (e.g. sentiment.py) |
| L | 1–2 days | Full phase subsection (e.g. all of Phase 0) |
| XL | 3–5 days | Complete phase |

Update `docs/progress.md` when completing each phase exit criterion.
