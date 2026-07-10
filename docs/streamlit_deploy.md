# Streamlit Community Cloud deployment

## Prerequisites

- Private GitHub repo pushed (`djmobeus/stock-analyzer`)
- Supabase project with schema initialised (`python scripts/init_db.py`)
- `DATABASE_URL` in GitHub Actions secrets (already done)

## Deploy steps

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **New app** → select `djmobeus/stock-analyzer`, branch `main`.
3. Main file path: `app/streamlit_app.py`
4. Advanced settings → Python version **3.11**
5. Secrets (TOML format):

```toml
DATABASE_URL = "postgresql://..."
APP_PASSWORD = "your-chosen-password"
```

6. Deploy. First build installs `requirements-core.txt` automatically if you add a `packages.txt` or specify in repo — Streamlit Cloud reads `requirements.txt` by default.

**Live app:** [https://stock-analyzer-djmobeus.streamlit.app/](https://stock-analyzer-djmobeus.streamlit.app/)

> On the free tier the app **sleeps** when nobody visits it. Click **Relaunch** to wake it. This does **not** affect the nightly email (that runs on GitHub Actions).

### Recommended: root `requirements.txt` for cloud

Streamlit Cloud uses `requirements.txt` at repo root. The full file includes optional heavy deps (torch). For faster deploys, create a **Streamlit-only** install by pointing Cloud to `requirements-core.txt` in the app settings, or keep `requirements-core.txt` as the primary file.

## Verify

- Home page shows latest scan date and observation counts
- Morning scan loads candidates from Supabase
- Portfolio reads observations across devices (shared DB)

## Nightly pipeline

GitHub Actions runs `scripts/run_nightly.py` on schedule (**05:00 UK Mon–Fri**). Morning report artifact uploaded for 7 days.

Emails are sent from GitHub Actions, not Streamlit. If emails stop, check **Actions** tab for failed or disabled scheduled runs.

## Local vs cloud

| | Local | Cloud |
|---|-------|-------|
| Database | SQLite `data/stock_analyzer.db` | Supabase via `DATABASE_URL` |
| Pipeline | `python scripts/run_nightly.py` | GitHub Actions |
| Dashboard | `streamlit run app/streamlit_app.py` | Streamlit Community Cloud |
