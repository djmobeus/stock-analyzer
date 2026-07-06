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

## Quick start (local development)

### Prerequisites

- Python 3.11+
- Git
- [Finnhub](https://finnhub.io/register) free API key

### Setup

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add FINNHUB_API_KEY
```

### Run (once implemented)

```powershell
python scripts/run_nightly.py      # Nightly pipeline
streamlit run app/streamlit_app.py # Dashboard
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
- **Data APIs:** £0 (yfinance, Finnhub free tier, RSS)
- **Optional LLM:** ~£3–5/month (Anthropic Haiku for morning summaries only)

## License

Private project — not for distribution.
