# 100% Cloud Setup — No Local PC Required

This guide makes the UK Stock Analyzer fully independent of your computer.

## Architecture (all free)

| Component | Service | Your PC needed? |
|-----------|---------|-----------------|
| Nightly scan (05:00 UK Mon–Fri) | GitHub Actions | No |
| Database | Supabase PostgreSQL | No |
| Dashboard (phone/laptop browser) | Streamlit Community Cloud | No |
| Morning email | Gmail SMTP from GitHub Actions | No |

---

## Checklist

### 1. Supabase (database) — likely done

- [x] Project created
- [x] `DATABASE_URL` in local `.env`
- [ ] Run schema on Supabase if `holdings` table missing:

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
.venv\Scripts\activate
python scripts/init_db.py
```

(Uses `DATABASE_URL` from `.env` when set.)

### 2. GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions**

| Secret | Required | Example |
|--------|----------|---------|
| `DATABASE_URL` | Yes | `postgresql://postgres:...@db....supabase.co:5432/postgres` |
| `EMAIL_TO` | Yes | `you@p-mouzakis.com` |
| `SMTP_USER` | Yes | Your Gmail address |
| `SMTP_PASSWORD` | Yes | Google [App Password](https://myaccount.google.com/apppasswords) |
| `EMAIL_FROM` | Yes | Same as SMTP_USER |
| `SMTP_HOST` | Optional | `smtp.gmail.com` (default) |
| `SMTP_PORT` | Optional | `587` (default) |
| `ANTHROPIC_API_KEY` | Optional | For Haiku morning prose |
| `FINNHUB_API_KEY` | Optional | Not needed for UK |

**PowerShell (gh CLI):**

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" secret set DATABASE_URL
& "C:\Program Files\GitHub CLI\gh.exe" secret set EMAIL_TO
& "C:\Program Files\GitHub CLI\gh.exe" secret set SMTP_USER
& "C:\Program Files\GitHub CLI\gh.exe" secret set SMTP_PASSWORD
& "C:\Program Files\GitHub CLI\gh.exe" secret set EMAIL_FROM
& "C:\Program Files\GitHub CLI\gh.exe" secret set ANTHROPIC_API_KEY
```

### 3. Push latest code to GitHub

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
git add -A
git commit -m "Cloud schedule, email digest, II import"
git push
```

### 4. Streamlit Community Cloud (dashboard)

1. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
2. **New app** → repo `djmobeus/stock-analyzer`, branch `main`
3. Main file: `app/streamlit_app.py`
4. **Secrets** (TOML):

```toml
DATABASE_URL = "postgresql://..."
```

5. Deploy. Bookmark the URL on your phone.

The dashboard reads candidates, observations, and holdings from Supabase — same data as the nightly pipeline.

### 5. Verify GitHub Actions

1. Repo → **Actions** → **Nightly Pipeline**
2. **Run workflow** (manual test) — or wait until 05:00 UK Mon–Fri
3. Check run logs for `email_status: sent`
4. Download **morning-report** artifact if email fails

### 6. Gmail setup (for morning email)

1. Use a Gmail account as sender (`SMTP_USER`)
2. Enable 2FA on Google account
3. Create an **App Password** (not your normal password)
4. Set `EMAIL_TO` to your inbox at **p-mouzakis.com** (or Gmail)

If you use Google Workspace for `p-mouzakis.com`, SMTP may be `smtp.gmail.com` with your workspace address.

---

## Schedule

| Setting | Value |
|---------|-------|
| Run time | **05:00 UK** Mon–Fri |
| GitHub cron | `0 4` and `0 5 UTC` (covers BST/GMT) |
| Python gate | Only one run per day at 05:00 UK |

You receive:
- Email to `EMAIL_TO` with prose summary + HTML report
- Dashboard updated in Supabase
- Optional Anthropic Haiku narrative if API key set

---

## What you can turn off locally

Once cloud is verified:

- Stop local `streamlit run` — use Streamlit Cloud URL instead
- Stop local nightly runs — GitHub Actions handles it
- PC can be off overnight and when travelling

Local development remains useful for testing (`--force --limit 5`) but is not required for daily use.

---

## Optional features included

| Feature | Config |
|---------|--------|
| Anthropic morning prose | `ANTHROPIC_API_KEY` |
| Email digest | SMTP secrets + `EMAIL_TO` |
| II holdings import | Streamlit → **Holdings** page (upload CSV) |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Email not sent | Check SMTP secrets; verify App Password |
| Dashboard empty | Confirm Streamlit `DATABASE_URL` matches GitHub |
| Pipeline skipped `outside_run_window` | Normal for one of the two UTC crons; other should run |
| Pipeline skipped `already_completed_today` | Expected if manual re-run same day |
| Holdings table error | Run `python scripts/init_db.py` against Supabase |
