# Improving catalyst coverage

Catalysts used to come only from RSS headlines that happened to include a clear date —
so the database often stayed empty.

## What we do now

1. **Yahoo calendars** (primary) — earnings / ex-dividend dates via yfinance for the scorable universe each night  
2. **RSS extraction** (secondary) — improved UK date formats (`15 Sept 2026`, `7th July`, year inferred)  
3. **8-week window** — matches the hold period for scoring “upcoming” catalysts  
4. **Live refresh in the app** — if tonight’s shortlist was scored before calendars filled, the UI can still show a catalyst once it exists in the DB  

## Limits

Yahoo coverage is uneven for some LSE names. “No clear dated catalyst” can still appear — then check RNS / company site manually.
