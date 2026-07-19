# UK Stock Analyzer

Nightly screening for FTSE 100/250 — technicals, fundamentals, news, and learning over time. Morning email + cloud web app.

**Not financial advice.** Personal analytical tool only.

## Status (rebuild v2)

| Layer | Status |
|-------|--------|
| Nightly pipeline + email | Active (GitHub Actions + Supabase) |
| **Primary UI** | **FastAPI + HTMX** (`webapp/`) — deploy on Render/Railway |
| Streamlit (`app/`) | **Legacy** — do not use as primary |

**Start here:** [docs/rebuild_plan.md](docs/rebuild_plan.md) · [docs/rebuild_brief.md](docs/rebuild_brief.md)

## Documentation

| Document | Description |
|----------|-------------|
| [docs/rebuild_plan.md](docs/rebuild_plan.md) | Full rebuild plan (phases R0–R7) |
| [docs/rebuild_brief.md](docs/rebuild_brief.md) | Why rebuild, goals, success criteria |
| [project_spec.md](project_spec.md) | Product goals and user profile |
| [docs/architecture.md](docs/architecture.md) | v2 system design |
| [docs/ux_spec.md](docs/ux_spec.md) | Screens and coaching loop |
| [docs/data_quality.md](docs/data_quality.md) | Prices, tickers, filters |
| [docs/decisions.md](docs/decisions.md) | ADRs |
| [docs/tasks.md](docs/tasks.md) | Rebuild checklist |
| [docs/progress.md](docs/progress.md) | Progress tracker |
| [docs/cloud_setup.md](docs/cloud_setup.md) | Cloud secrets and schedule |
| [docs/webapp_deploy.md](docs/webapp_deploy.md) | FastAPI deploy (Render/Railway) |

## Quick start (local)

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env — DATABASE_URL, APP_PASSWORD, optional ANTHROPIC_API_KEY
python scripts/init_db.py
python -m pytest tests/ -q
```

### Pipeline

```powershell
python scripts/run_nightly.py --force --limit 5
```

### Web app (v2)

```powershell
python -m uvicorn webapp.main:app --reload --reload-dir webapp --reload-dir src --reload-dir config
# open http://127.0.0.1:8000
```

### Legacy Streamlit (optional)

```powershell
streamlit run app/streamlit_app.py
```

## Hosting

| Component | Service |
|-----------|---------|
| Nightly pipeline | GitHub Actions (~05:00 UK, email by ~07:00) |
| Database | Supabase PostgreSQL |
| Web UI | Render or Railway (FastAPI) |
| Email | Gmail SMTP from Actions |

## License

Private project — not for distribution.
