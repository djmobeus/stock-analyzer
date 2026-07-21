# 100% Cloud Setup — No Local PC Required (v2)

## Architecture

| Component | Service | Your PC needed? |
|-----------|---------|-----------------|
| Nightly scan (~03:00 UK Mon–Fri, email by ~05:00) | GitHub Actions | No |
| Database | Supabase PostgreSQL | No |
| **Web app (primary)** | **Render or Railway (FastAPI)** | No |
| Morning email | Gmail SMTP from GitHub Actions | No |
| Legacy dashboard | Streamlit Community Cloud (optional) | No |

> **Emails do not depend on the web app.** GitHub Actions sends email. If the web app is asleep/redeploying, you still get the digest when the pipeline finishes.

See [webapp_deploy.md](webapp_deploy.md) for FastAPI hosting.

---

## Checklist

### 1. Supabase

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
.venv\Scripts\activate
python scripts/init_db.py
```

### 2. GitHub Actions secrets

| Secret | Required |
|--------|----------|
| `DATABASE_URL` | Yes |
| `EMAIL_TO` | Yes |
| `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | Yes |
| `ANTHROPIC_API_KEY` | Optional (prose + coaching) |
| `APP_BASE_URL` | Optional — your Render URL so morning email links to `/shortlist` |

### 3. Schedule (v2)

| Setting | Value |
|---------|-------|
| Preferred start | ~03:00 UK Mon–Fri |
| Results aimed by | **05:00 UK** |
| Crons | One primary UTC cron for BST + one for GMT (DST); **cancel-in-progress: true** |
| Gate | One successful run/day; late starts still run |

**Why jobs used to pile up:** Multiple crons + `cancel-in-progress: false` left a second run waiting. GitHub also often starts cron 30–90 minutes late.

### 4. Web app secrets (Render/Railway)

```
DATABASE_URL=postgresql://...
APP_PASSWORD=your-password
ANTHROPIC_API_KEY=optional
```

### 5. Verify

1. Actions → Run workflow (force, empty limit) once after schedule changes
2. Log contains `status: success` and `email_status: sent` (or `SKIPPED:` if already done)
3. Open FastAPI URL → login → shortlist shows **names** and today’s scan

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Short green run, no email | Search log for `SKIPPED` / `status: skipped` |
| Two runs queued | Ensure workflow has `cancel-in-progress: true` and only DST pair of crons |
| App slow | Use FastAPI host, not Streamlit |
| Blank Latest on holdings | Ticker not in last scan prices; wait for next run or use live fallback |
| Investing.com wrong page | Use mapped slug or Yahoo link (see data_quality.md) |
