# FastAPI web app deploy (v2)

Primary UI replaces Streamlit. Same Supabase `DATABASE_URL`.

## Local

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
.venv\Scripts\activate
pip install -r requirements.txt
# .env: DATABASE_URL, APP_PASSWORD, SESSION_SECRET (optional), ANTHROPIC_API_KEY (optional)
python -m uvicorn webapp.main:app --reload --reload-dir webapp --reload-dir src --reload-dir config
```

Open http://127.0.0.1:8000

If the terminal loops on `WatchFiles detected changes… Reloading…`, press Ctrl+C and run without reload:

```powershell
python -m uvicorn webapp.main:app
```

(Dropbox syncing `.venv` can trigger endless reloads.)

## Render

1. New **Web Service** → connect `djmobeus/stock-analyzer`
2. Runtime: Python 3.11
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn webapp.main:app --host 0.0.0.0 --port $PORT`
5. Env vars: `DATABASE_URL`, `APP_PASSWORD`, `SESSION_SECRET`, optional `ANTHROPIC_API_KEY`, optional `APP_BASE_URL` (your Render URL — adds a shortlist link in the morning email)

## Railway

1. New project from GitHub repo
2. Start command: `uvicorn webapp.main:app --host 0.0.0.0 --port $PORT`
3. Same env vars as Render

## Notes

- Email still comes from GitHub Actions — not from this service
- Run `python scripts/init_db.py` once after pull (adds `analysis_notes` / `shortlist_feedback` tables)
- Streamlit Cloud can be **paused** once you are happy with the Render URL
- Free Render sleeps when idle; first open after sleep can take ~30–60s. For snappier mornings, upgrade later.