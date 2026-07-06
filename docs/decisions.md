# Technology Decisions

This document records key architectural and technology choices, the rationale behind them, and alternatives considered.

---

## ADR-001: Python as the sole language

**Decision:** Use Python 3.11+ for pipeline, analysis, ML, and dashboard.

**Why:**
- Widest ecosystem for finance data (pandas, yfinance, pandas-ta, scikit-learn)
- Streamlit allows dashboard without learning JavaScript
- Project owner is not a professional developer — one language reduces complexity

**Alternatives rejected:**
- Node.js + React — two languages, more boilerplate
- Jupyter notebooks only — not suitable for scheduled production pipeline

---

## ADR-002: SQLite for local dev; Supabase for cloud

**Decision:** SQLite during development; Supabase PostgreSQL (free tier) when deploying to Streamlit Cloud and GitHub Actions.

**Why:**
- SQLite: zero setup, perfect for learning and local runs
- Supabase: free PostgreSQL accessible from both GitHub Actions and Streamlit Cloud
- Same SQL schema with minor dialect handling in `connection.py`

**Alternatives rejected:**
- SQLite on Streamlit Cloud — ephemeral filesystem, data lost on restart
- Paid managed Postgres (Railway, Neon paid) — unnecessary cost
- Vercel KV / serverless DB — wrong platform for this stack

---

## ADR-003: GitHub Actions for nightly pipeline (not Vercel)

**Decision:** Schedule the nightly batch via GitHub Actions cron workflow.

**Why:**
- Free for private repos (2,000 minutes/month — nightly job ~15 min ≈ 330 min/month)
- Runs when local PC is off
- Native secret management for API keys
- No server to maintain

**Alternatives rejected:**
- **Vercel** — designed for Next.js serverless; 10–60s timeout, no Python batch jobs, no SQLite
- **Railway / Render free tier** — limited hours or sleep; less predictable
- **Local PC only** — user preference is online when machine is off
- **Oracle Cloud Free VM** — valid backup if GitHub minutes exhausted; more DevOps overhead

---

## ADR-004: Streamlit Community Cloud for dashboard

**Decision:** Host dashboard on Streamlit Community Cloud (free).

**Why:**
- Native Streamlit hosting, connects to GitHub repo
- Mobile browser access for morning checks
- No server management

**Alternatives rejected:**
- Vercel — does not host Streamlit/Python dashboards natively
- Self-hosted on Oracle VM — more setup for v1
- Localhost only — fails "PC may be off" requirement

---

## ADR-005: yfinance as primary price source with validation layer

**Decision:** Use yfinance for OHLCV; mandatory GBX normalisation and quarantine; Finnhub cross-check on suspicious tickers.

**Why:**
- Free, covers all LSE `.L` tickers
- Known GBp/GBP inconsistency issues — addressed by validation, not avoided by paid data in v1

**Alternatives rejected:**
- Paid LSEG/refinitiv — far beyond budget
- yfinance without validation — unacceptable accuracy risk for investment decisions

---

## ADR-006: Finnhub free tier for fundamentals and analyst data

**Decision:** Finnhub for analyst recommendations, price targets, company profile, and financials.

**Why:**
- Free tier: 60 calls/minute, sufficient for ~150 stocks nightly with caching
- Structured JSON API — no fragile web scraping
- Covers analyst count filter (4+ analysts)

**Alternatives rejected:**
- Stockopedia / Simply Wall St scraping — breaks often, ToS risk, maintenance burden
- yfinance alone — incomplete analyst coverage for FTSE 250

---

## ADR-007: pandas-ta for technical indicators (not TA-Lib)

**Decision:** pandas-ta as primary indicator library.

**Why:**
- Pure Python/pandas — easy install on Windows, no C compiler
- Covers all required indicators (SMA, RSI, MACD, OBV, etc.)

**Alternatives rejected:**
- TA-Lib — C dependency, painful on Windows, marginal benefit

---

## ADR-008: Hybrid intelligence — local default, optional paid LLM

**Decision:**
- **Default (free):** VADER + FinBERT for sentiment; regex for RNS catalysts; Jinja2 templates for morning briefings; sentence-transformers for pattern matching
- **Optional upgrade (~£3–5/mo):** Anthropic Haiku for morning prose summaries and ambiguous catalyst extraction

**Why:**
- Investment accuracy depends on **data and indicators**, not LLM prose
- FinBERT is peer-reviewed for financial sentiment — often better than generic LLM on headlines
- Structured output ("RSI 32, 4.2% from support, catalyst in 18 days") is more actionable than narrative
- User wants free but not at cost of bad analysis — hybrid preserves quality where it matters

**Alternatives rejected:**
- Anthropic-only (original spec) — ~£8–15/mo ongoing cost
- Ollama-only — good for extraction but adds local PC dependency for inference
- No sentiment at all — loses catalyst/news layer value

---

## ADR-009: scikit-learn for ML (not deep learning)

**Decision:** scikit-learn Random Forest / logistic regression with walk-forward cross-validation.

**Why:**
- Works on small datasets (100–500 observations)
- Interpretable feature importance
- Runs free on CPU in GitHub Actions
- Random Forest robust to mixed feature types and small sample overfitting

**Alternatives rejected:**
- Neural networks — need thousands of samples, opaque, overkill
- Cloud ML services — cost and complexity

**Minimum data thresholds:**
- <100 outcomes: composite score only, no ML predictions shown
- 100–300 outcomes: logistic regression
- 300+ outcomes: Random Forest with pruned features

---

## ADR-010: Shadow logging all nightly candidates

**Decision:** Automatically log top 15 candidates each night with full feature snapshot; track outcomes for all.

**Why:**
- User-only logging creates biased, slow-to-grow dataset
- Unbiased shadow data enables earlier ML and backtest validation
- Core to "system learns over time" goal

---

## ADR-011: Walk-forward validation (never random train/test split)

**Decision:** Time-series aware cross-validation for all ML training and backtests.

**Why:**
- Financial data is temporal — random splits leak future information
- Walk-forward mimics real deployment (train on past, predict forward)

---

## ADR-012: Explicit composite score weights in config.yaml

**Decision:** Store scoring weights in versioned config file; snapshot weights per scan run.

**Why:**
- Transparent, tunable without code changes
- Reproducible — know which weights produced which candidates
- Backtest can optimise weights before ML layer

**Starting weights:**
```
support_proximity:     0.25
multi_tf_confluence:   0.20
analyst_upside:        0.15
catalyst_proximity:    0.15
news_sentiment:        0.10
market_regime:         0.10
sector_relative:       0.05
```

---

## ADR-013: No microservices or unnecessary frameworks

**Decision:** Monolithic Python package; CLI entry points; no FastAPI/Django/Celery in v1.

**Why:**
- Solo non-developer owner — simplicity over scalability
- ~150 stocks nightly does not need distributed architecture
- Can extract FastAPI later if needed

---

## ADR-014: Private GitHub repository

**Decision:** Host code in a private GitHub repo.

**Why:**
- GitHub Actions scheduling requires GitHub
- Streamlit Cloud deploys from GitHub
- Keeps API key patterns and personal trading logic private

---

## ADR-015: Cursor Auto mode for development

**Decision:** Use Cursor Auto as default model; Plan mode for phase kickoffs; manual Opus only for stubborn data bugs.

**Why:**
- Efficient use of included Cursor usage
- Auto routes appropriately for most Python/data tasks
- GBp/pence bugs are the main case for manual escalation

---

## Decision log

| ID | Date | Decision | Status |
|----|------|----------|--------|
| ADR-001 | 2026-07-06 | Python monolith | Accepted |
| ADR-002 | 2026-07-06 | SQLite local / Supabase cloud | Accepted |
| ADR-003 | 2026-07-06 | GitHub Actions cron | Accepted |
| ADR-004 | 2026-07-06 | Streamlit Community Cloud | Accepted |
| ADR-005 | 2026-07-06 | yfinance + validation | Accepted |
| ADR-006 | 2026-07-06 | Finnhub free tier | Accepted |
| ADR-007 | 2026-07-06 | pandas-ta | Accepted |
| ADR-008 | 2026-07-06 | Hybrid local/paid LLM | Accepted |
| ADR-009 | 2026-07-06 | scikit-learn ML | Accepted |
| ADR-010 | 2026-07-06 | Shadow logging | Accepted |
| ADR-011 | 2026-07-06 | Walk-forward CV | Accepted |
| ADR-012 | 2026-07-06 | Config-driven scoring | Accepted |
| ADR-013 | 2026-07-06 | No microservices v1 | Accepted |
| ADR-014 | 2026-07-06 | Private GitHub repo | Accepted |
| ADR-015 | 2026-07-06 | Cursor Auto for dev | Accepted |
