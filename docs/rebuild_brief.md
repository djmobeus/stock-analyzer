# Rebuild Brief (v2)

Last updated: 2026-07-14

## Why rebuild

The v1 system (GitHub Actions + Supabase + Streamlit) proved the pipeline and email path work, but the **product experience** does not:

- Streamlit Community Cloud is too slow to use day-to-day
- Morning schedule is unreliable (late starts, queued duplicate runs, missed emails)
- Shortlist trust is weak (names missing, Investing.com search links, price/chart mismatches)
- Charts are hard to use
- ML status is opaque
- “Why was this stock chosen?” is not clear enough
- There is no coaching loop on the user’s own analysis

## Goals

1. **Usable cloud UI** — FastAPI + HTMX (not Streamlit) on Render/Railway
2. **Reliable mornings** — one weekday pipeline; email aimed before **07:00 UK**
3. **Trust** — company name + ticker; correct chart links; clear price source
4. **Usable charts** — TradingView Lightweight Charts
5. **Explainability** — per-stock “why shortlisted” (factors + catalysts + conflicts)
6. **Coaching** — user writes analysis → honest AI critique (no flattery)
7. **ML honesty** — clear inactive/active status and what is being learned

## Non-goals (v2)

- Not moving the batch job to Vercel
- Not switching to a paid primary price API unless yfinance fails audit
- Not claiming ML edge before ~100 labelled 8-week outcomes
- Not keeping Streamlit as the primary UI

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | Weekday email most days before 07:00 UK (or clear “running late” status) |
| 2 | Only one full pipeline per weekday |
| 3 | App usable on phone; chart zoom/pan works |
| 4 | Every shortlisted stock shows name + why chosen + catalysts |
| 5 | Chart/external link opens the right instrument ≥90% for shortlist |
| 6 | User can store analysis + blunt AI critique |
| 7 | ML status obvious on one screen |

## Work order

1. Docs (this pack) → 2. R0 schedule → 3. R2 UI → 4. R3 trust/charts → 5. R4 why-chosen → 6. R6 coaching → 7. R5 ML + R7 polish

## Legacy

- Streamlit app under `app/` is **legacy** (optional temporary read-only)
- Primary UI: `webapp/` (FastAPI)
