# UK Stock Analyzer

Nightly screening system for FTSE 100 and FTSE 250 stocks — technical analysis, fundamentals, news sentiment, and machine learning to surface high-probability trade candidates each morning.

**Not financial advice.** Analytical tool for personal use only.

## Documentation

| Document | Description |
|----------|-------------|
| [project_spec.md](project_spec.md) | Product goals, user profile, features |
| [docs/architecture.md](docs/architecture.md) | System design, hosting, APIs |
| [docs/decisions.md](docs/decisions.md) | Technology choices and rationale |
| [docs/tasks.md](docs/tasks.md) | Development roadmap |
| [docs/progress.md](docs/progress.md) | Progress tracker |
| [docs/cloud_setup.md](docs/cloud_setup.md) | **100% cloud setup (no PC required)** |
| [docs/streamlit_deploy.md](docs/streamlit_deploy.md) | Streamlit Cloud deployment |

## Quick start (local development)

### Prerequisites

- Python 3.11+
- Git
- Supabase `DATABASE_URL` (or leave empty for local SQLite)

### Setup

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-core.txt
copy .env.example .env
# Edit .env — add DATABASE_URL (optional Finnhub key)
python scripts/init_db.py
python scripts/run_phase0_validation.py
python -m pytest tests/ -v
```

### Run

```powershell
python scripts/run_nightly.py --force   # Nightly pipeline (add --limit 5 to test)
python scripts/run_outcomes.py          # Update 2/4/8-week outcomes
python scripts/run_backtest.py          # Backtest shadow candidates
streamlit run app/streamlit_app.py      # Dashboard
```

## Hosting (free, PC can be off)

| Component | Service | Cost |
|-----------|---------|------|
| Nightly pipeline | GitHub Actions (cron) | £0 |
| Dashboard | Streamlit Community Cloud | £0 |
| Database (cloud) | Supabase free tier | £0 |

**Vercel is not used** — it does not support Python batch jobs or long-running scheduled tasks.

## Learning over time

The system improves as you use it:

- **Shadow logging** — every nightly scan records top candidates automatically
- **Outcome tracking** — 2/4/8-week results labelled without manual input
- **Pattern stats** — hit rates per setup type after ~30 samples
- **ML predictions** — appear after 100+ labelled outcomes

Months 1–3 rely on rule-based composite scoring. ML augments later.

## Cost

- **Infrastructure:** £0/month (GitHub Actions + Streamlit Cloud + Supabase)
- **Data APIs:** £0 (yfinance, RSS; Finnhub optional)
- **Optional LLM:** ~£3–5/month (Anthropic Haiku for morning summaries only)

## License

Private project — not for distribution.
