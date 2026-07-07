# Progress Tracker

Last updated: 2026-07-07

## Overall status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| — | Project foundation | Complete | ██████████ 100% |
| 0 | Data validation | Complete | ██████████ 100% |
| 1 | Core pipeline | Complete | ██████████ 100% |
| 2 | Fundamentals & news | Complete | ██████████ 100% |
| 3 | Scoring & shadow log | Complete | ██████████ 100% |
| 4 | User observations | Complete | ██████████ 100% |
| 5 | Machine learning | Complete | ██████████ 100% |
| 6 | Dashboard & automation | Complete | ██████████ 100% |

---

## Completed work

### 2026-07-06 — Project foundation

- [x] Initial spec analysis and architecture review
- [x] Cost strategy defined (£0 infrastructure, optional ~£3–5/mo LLM)
- [x] Hosting decision: GitHub Actions + Streamlit Cloud (not Vercel)
- [x] `project_spec.md` created
- [x] `docs/architecture.md` created
- [x] `docs/decisions.md` created
- [x] `docs/progress.md` created (this file)
- [x] `docs/tasks.md` created
- [x] `.cursor/rules` created
- [x] Initial git commit on `main` branch
- [x] `docs/github_setup.md` — private repo instructions
- [x] Private GitHub repository created and pushed (`djmobeus/stock-analyzer`)
- [x] Supabase project created
- [x] `DATABASE_URL` in local `.env` (gitignored)
- [x] `DATABASE_URL` in GitHub Actions secrets (user confirmed)
- [x] Python virtual environment (`.venv`) and core dependencies installed
- [x] `src/` package scaffold (config, data, db)
- [x] Database schema created on Supabase
- [x] Phase 0 complete — 30/30 tickers pass (0% quarantine rate)
- [x] See `docs/phase0_report.md`

### 2026-07-07 — Phase 0 data validation

- [x] `src/data/prices.py` — yfinance fetch + GBX normalisation
- [x] `src/data/quality.py` — sanity checks and quarantine
- [x] `src/data/finnhub_client.py` — optional cross-validation
- [x] `src/db/schema.sql` + `connection.py` + `repositories.py`
- [x] `scripts/init_db.py` and `scripts/run_phase0_validation.py`
- [x] 7 pytest tests passing

---

## Current focus

### 2026-07-07 — Cloud & optionals

- [x] Schedule moved to **05:00 UK Mon–Fri**
- [x] GitHub Actions dual-cron + once-per-day gate
- [x] Email morning digest (Gmail SMTP → `EMAIL_TO`)
- [x] Anthropic Haiku prose in report + email
- [x] Interactive Investor CSV import (Holdings page)
- [x] `docs/cloud_setup.md` — full cloud checklist

All core phases implemented. Optional upgrades remain: Anthropic morning prose, email digest, II CSV import.

---

### 2026-07-07 — Phase 5 & 6 completion

- [x] ML model (`intelligence/ml_model.py`) — logistic regression / random forest with walk-forward CV
- [x] Text similarity for chart descriptions (TF-IDF + optional sentence-transformers)
- [x] Shadow candidate outcome tracking
- [x] Backtest module + `scripts/run_backtest.py`
- [x] Plotly candlestick charts on morning scan and lookup
- [x] ML probability on morning scan + HTML report
- [x] Feature importance on patterns page
- [x] Streamlit deploy guide (`docs/streamlit_deploy.md`)
- [x] GitHub Actions failure annotation

### 2026-07-07 — Phase 4 user observations

- [x] Observation logging with feature snapshot (`observations/service.py`)
- [x] Chart description → pattern tags (`intelligence/patterns.py`)
- [x] Automated 2/4/8-week outcome tracking (`pipeline/outcomes.py`)
- [x] Pattern hit-rate statistics (`pattern_stats` table)
- [x] Streamlit pages: morning scan, portfolio, patterns, lookup
- [x] Outcomes wired into nightly pipeline

### 2026-07-07 — Phase 3 scoring

- [x] Support/resistance detection (`support_resistance.py`)
- [x] Composite scoring with config weights (`scoring.py`)
- [x] Shadow-log top 15; morning shortlist top 10 (`scoring_step.py`)
- [x] HTML morning report (`reports/morning_report.py`)
- [x] Fundamentals switched from Finnhub to yfinance (UK LSE)
- [x] Phase 3 pytest coverage

### 2026-07-07 — Phase 2 fundamentals update

- [x] yfinance for analyst data and filters 4–6
- [x] `FINNHUB_API_KEY` now optional in `.env.example`

## Remaining work (summary)

See [tasks.md](tasks.md) for full breakdown.

| Milestone | Target | Blockers |
|-----------|--------|----------|
| Phase 0 complete | TBD | GitHub repo, Python env |
| First nightly run (local) | TBD | Phase 0 + 1 |
| First morning candidates | TBD | Phase 1 + 2 + 3 |
| First user observation logged | TBD | Phase 4 |
| ML predictions live | TBD | 100+ shadow outcomes |
| Cloud deployment live | TBD | Phase 6, Supabase setup |

---

## Learning system maturity

Track how the self-improvement loop develops over time.

| Metric | Current | Threshold for ML | Notes |
|--------|---------|------------------|-------|
| Shadow-logged candidates | 0 | — | Auto from first nightly run |
| User observations | 0 | — | Phase 4 |
| Labelled outcomes (2/4/8w) | 0 | 100 for ML | Grows weekly after first scan |
| Unique pattern types | 0 | 30 per type for stats | From chart descriptions |
| ML model version | — | v1 at 100+ labels | Walk-forward CV required |

---

## Risks and blockers

| Risk | Status | Mitigation |
|------|--------|------------|
| yfinance GBp/GBP errors | Open | Phase 0 validation spike |
| Supabase setup | Done | `DATABASE_URL` in `.env` + GitHub |
| Finnhub API key | Resolved | Optional; UK fundamentals use yfinance |
| Finnhub rate limits | N/A | Not used for UK pipeline |
| GitHub Actions minutes | Low risk | ~330 min/month of 2,000 limit |
| ML cold start | Expected | Composite score until 100+ outcomes |

---

## Changelog

### 2026-07-06
- Project initiated
- Foundation documentation created
- Architecture finalised: GitHub Actions + Streamlit Cloud + Supabase
- GitHub repo live (`djmobeus/stock-analyzer`)
- Supabase configured; `DATABASE_URL` in `.env` and GitHub secrets

### 2026-07-07 (Phase 3)
- Scoring pipeline: support/resistance, composite rank, shadow log, morning HTML report
- Fundamentals provider switched to yfinance for UK LSE tickers

### 2026-07-07 (Phase 2)
- Finnhub analyst data, filters 4–6 (analyst count, trust/REIT, FCF)
- RSS news ingestion (Proactive, Investegate)
- VADER sentiment scoring
- Catalyst extraction from RNS/news headlines
- 20 pytest tests passing
- Supabase schema initialised
- Core Python package built; 7 tests passing
