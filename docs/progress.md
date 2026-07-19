# Progress Tracker (Rebuild v2)

Last updated: 2026-07-19

## Overall status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| R1 | Docs + product spec | Complete | ██████████ 100% |
| R0 | Schedule reliability | Complete | ██████████ 100% |
| R2 | FastAPI UI (replace Streamlit) | Complete | ██████████ 100% |
| R3 | Names, links, charts | Complete | ██████████ 100% |
| R4 | Why shortlisted | Complete | ██████████ 100% |
| R5 | ML transparency | Complete | ██████████ 100% |
| R6 | Coaching conversation | Complete | ██████████ 100% |
| R7 | UX polish | Complete | ██████████ 100% |

## What this means for you

| Piece | Status |
|-------|--------|
| New FastAPI app code (`webapp/`) | **Done** on your PC |
| Nightly email pipeline | **Running** (GitHub Actions) |
| Earlier email schedule (~03:00 UK start) | **Updated** — needs push to GitHub to take effect |
| Hosted cloud URL for the new app | **Not yet** — you still open it locally, or deploy to Render (see below) |
| Streamlit | **Legacy** — do not use as primary |

### How to open the app today (local)

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
.venv\Scripts\activate
python -m uvicorn webapp.main:app
```

Then open http://127.0.0.1:8000 and log in with `APP_PASSWORD` from `.env`.

### How to host it (cloud URL on phone)

Follow [webapp_deploy.md](webapp_deploy.md) — Render or Railway. Needs the rebuild **pushed to GitHub** first.

## Shipped

- FastAPI + HTMX UI (home, shortlist, stock, holdings, notes, ML, lookup)
- TradingView charts; Yahoo/Investing links; why_chosen; coaching
- Connection reuse + shortlist speed fix
- Schedule aimed earlier: prefer 03:00 UK, results by ~05:00 UK
