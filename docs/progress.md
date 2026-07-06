# Progress Tracker

Last updated: 2026-07-06

## Overall status

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| — | Project foundation | In progress | ████░░░░░░ 40% |
| 0 | Data validation | Not started | ░░░░░░░░░░ 0% |
| 1 | Core pipeline | Not started | ░░░░░░░░░░ 0% |
| 2 | Fundamentals & news | Not started | ░░░░░░░░░░ 0% |
| 3 | Scoring & shadow log | Not started | ░░░░░░░░░░ 0% |
| 4 | User observations | Not started | ░░░░░░░░░░ 0% |
| 5 | Machine learning | Not started | ░░░░░░░░░░ 0% |
| 6 | Dashboard & automation | Not started | ░░░░░░░░░░ 0% |

---

## Completed work

### 2026-07-06 — Project foundation

- [x] Initial spec analysis and architecture review
- [x] Cost strategy defined (£0 infrastructure, optional ~£3–5/mo LLM)
- [x] Hosting decision: GitHub Actions + Streamlit Cloud (not Vercel)
- [x] `project_spec.md` created
- [x] `docs/architecture.md` created
- [x] `docs/decisions.md` created
- [x] `docs/progress.md` created (this file)
- [x] `docs/tasks.md` created
- [x] `.cursor/rules` created
- [ ] Private GitHub repository created and initial push
- [ ] Python project scaffold (`src/`, `requirements.txt`, etc.)

---

## Current focus

**Phase: Project foundation**

Next actions:
1. Create private GitHub repo and push initial commit
2. Scaffold Python package structure
3. Begin Phase 0 — yfinance LSE data validation spike

---

## Remaining work (summary)

See [tasks.md](tasks.md) for full breakdown.

| Milestone | Target | Blockers |
|-----------|--------|----------|
| Phase 0 complete | TBD | GitHub repo, Python env |
| First nightly run (local) | TBD | Phase 0 + 1 |
| First morning candidates | TBD | Phase 1 + 2 + 3 |
| First user observation logged | TBD | Phase 4 |
| ML predictions live | TBD | 100+ shadow outcomes |
| Cloud deployment live | TBD | Phase 6, Supabase setup |

---

## Learning system maturity

Track how the self-improvement loop develops over time.

| Metric | Current | Threshold for ML | Notes |
|--------|---------|------------------|-------|
| Shadow-logged candidates | 0 | — | Auto from first nightly run |
| User observations | 0 | — | Phase 4 |
| Labelled outcomes (2/4/8w) | 0 | 100 for ML | Grows weekly after first scan |
| Unique pattern types | 0 | 30 per type for stats | From chart descriptions |
| ML model version | — | v1 at 100+ labels | Walk-forward CV required |

---

## Risks and blockers

| Risk | Status | Mitigation |
|------|--------|------------|
| yfinance GBp/GBP errors | Open | Phase 0 validation spike |
| GitHub CLI not installed | Open | Manual repo creation on github.com |
| Finnhub rate limits | Monitoring | Cache analyst data 7 days |
| GitHub Actions minutes | Low risk | ~330 min/month of 2,000 limit |
| ML cold start | Expected | Composite score until 100+ outcomes |

---

## Changelog

### 2026-07-06
- Project initiated
- Foundation documentation created
- Architecture finalised: GitHub Actions + Streamlit Cloud + Supabase
