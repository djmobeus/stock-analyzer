# GitHub Private Repository Setup

The local git repository is initialised with an initial commit. Follow these steps to create the private GitHub repo and push.

## Step 1 — Log in to GitHub CLI

Open a **new** PowerShell window (important — so `gh` is on your PATH after install), then run:

```powershell
gh auth login
```

If you see `gh : The term 'gh' is not recognized`, either:

1. **Close and reopen PowerShell** (or restart Cursor), then try again, or
2. **Use the full path** (works immediately):

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth login
```

To permanently fix PATH in your current session without restarting:

```powershell
$env:Path += ";C:\Program Files\GitHub CLI"
gh --version
```

Choose during login:
- **GitHub.com**
- **HTTPS**
- **Login with a web browser** (easiest)

## Step 2 — Create private repo and push

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"

# Rename branch to main (optional but recommended)
git branch -M main

# Create private repo on your GitHub account and push
gh repo create stock-analyzer --private --source=. --remote=origin --push
```

If you prefer a different repo name, replace `stock-analyzer`.

## Alternative — Create repo on github.com manually

1. Go to https://github.com/new
2. Repository name: `stock-analyzer` (or your choice)
3. Visibility: **Private**
4. Do **not** initialise with README (we already have one)
5. Click **Create repository**

Then in PowerShell:

```powershell
cd "c:\Users\PMouzakis\Dropbox\Stock Analyzer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/stock-analyzer.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 3 — Add GitHub Actions secrets

After the repo exists, add secrets for the nightly pipeline.

**Full cloud checklist:** see [docs/cloud_setup.md](cloud_setup.md)

If `gh` is not recognized, use the full path or refresh PATH first (see Step 1).

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" secret set DATABASE_URL
& "C:\Program Files\GitHub CLI\gh.exe" secret set EMAIL_TO
& "C:\Program Files\GitHub CLI\gh.exe" secret set SMTP_USER
& "C:\Program Files\GitHub CLI\gh.exe" secret set SMTP_PASSWORD
& "C:\Program Files\GitHub CLI\gh.exe" secret set EMAIL_FROM
& "C:\Program Files\GitHub CLI\gh.exe" secret set ANTHROPIC_API_KEY
```

Or add via GitHub web UI: **Settings → Secrets and variables → Actions → New repository secret**

## Step 4 — Deploy Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Select this repo, main branch, main file: `app/streamlit_app.py`
4. Add `DATABASE_URL` in Streamlit Cloud secrets

## Step 5 — Create Supabase project (Phase 6)

1. Go to https://supabase.com/ — free tier
2. Create project, copy PostgreSQL connection string
3. Use as `DATABASE_URL` in GitHub Actions and Streamlit secrets

---

## Verify

```powershell
gh repo view --web
git remote -v
```

You should see your private repo on GitHub with all foundation files.
