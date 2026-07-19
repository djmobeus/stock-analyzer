# Development Roadmap (Rebuild v2)

**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done

See also: [rebuild_plan.md](rebuild_plan.md), [rebuild_brief.md](rebuild_brief.md), [architecture.md](architecture.md), [ux_spec.md](ux_spec.md).

---

## Phase R1 — Docs

- [x] `docs/rebuild_brief.md`
- [x] Rewrite `docs/architecture.md` (v2)
- [x] Replace `docs/tasks.md` (this file)
- [x] Append v2 ADRs to `docs/decisions.md`
- [x] Reset `docs/progress.md`
- [x] `docs/ux_spec.md`
- [x] `docs/data_quality.md`
- [x] Update `docs/cloud_setup.md`, `project_spec.md`, `README.md`
- [x] `docs/webapp_deploy.md`

---

## Phase R0 — Schedule reliability

- [x] Single DST cron pair (04:00 / 05:00 UTC)
- [x] `concurrency.cancel-in-progress: true`
- [x] Late-run gate + `SKIPPED:` in logs
- [x] Web home: last scan / run status / results-by hour
- [x] Manual workflow_dispatch remains

---

## Phase R2 — Replace Streamlit

- [x] Scaffold `webapp/` FastAPI + Jinja
- [x] Login with `APP_PASSWORD`
- [x] Pages: home, shortlist, stock detail, holdings, notes, ml
- [x] Deploy docs for Render/Railway
- [x] Mark Streamlit legacy in README

---

## Phase R3 — Names, links, charts

- [x] Company name + ticker in email + UI
- [x] `data/investing_slugs.json` + Yahoo fallback
- [x] TradingView Lightweight Charts on stock detail
- [x] Price source disclaimer
- [x] Link helpers in `visualization/links.py`

---

## Phase R4 — Why shortlisted

- [x] Build `why_chosen` at score time
- [x] UI card + email bullets
- [x] Optional `conflict_penalty` in scoring config

---

## Phase R5 — ML transparency

- [x] `/ml` page: outcomes N/100, model meta, shadow hit rates
- [x] Plain English inactive vs active
- [x] Feature importance list

---

## Phase R6 — Coaching loop

- [x] `analysis_notes` table + repository
- [x] Honest Haiku critique (`intelligence/coaching.py`)
- [x] Store critique; show on detail/notes pages
- [x] Usage logging reuse

---

## Phase R7 — UX polish

- [x] Holdings single table + “Awaiting scan” for blank prices
- [x] Consistent terminology (timeframe conflict)
- [x] Mobile-friendly CSS
- [x] Clear home status metrics
- [x] Lookup page (`/lookup`)
- [x] Chart Daily / Weekly / Monthly + volume
- [x] Score breakdown on stock detail
- [x] Notes filters (ticker / awaiting critique)

---

## Follow-ups (ops / later tuning)

- [x] Earlier morning schedule (~03:00 UK start, aim ~05:00 email)
- [ ] **Commit + push** rebuild files to GitHub (required before deploy / earlier cron)
- [ ] Deploy FastAPI to Render/Railway and set secrets → you get a phone URL
- [ ] `python scripts/init_db.py` on Supabase (analysis_notes) if not done
- [ ] Expand `investing_slugs.json` as new names appear
- [ ] Pause Streamlit Cloud when happy with new URL
- [ ] Review shortlist “quality feel” after a week of why-chosen cards
- [ ] Optional: spot-check top 10 closes vs Investing.com weekly
