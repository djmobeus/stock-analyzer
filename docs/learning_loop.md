# Improving odds (learning loop)

Your goal: raise the chance of ~**+8% in 2–8 weeks** using filters, catalysts, charts, and feedback.

## What already learns without you

1. **Shadow log** — top ~15 suggestions every night  
2. **Outcomes** — price checked at 2 / 4 / 8 weeks vs +8% target / stop  
3. **Rule scores** — support, timeframes, catalysts, sentiment, regime  

## What you add (high leverage)

| Action | Why it helps |
|--------|----------------|
| **Keep / Drop** on shortlist | Labels “quality feel” so we can later see which Keep names hit +8% |
| **Chart notes on 1–3 names** | Your pattern recognition + honest coach critique |
| **Agree/disagree** with why-chosen | Captures when the system’s story matches your eye |

## Habits that improve odds more than more ML

1. Only deep-dive names you’d size a real position in  
2. Respect timeframe conflict flags unless you have a clear override  
3. Prefer names with a **dated catalyst** inside your 2–8 week window  
4. Review Keep/Drop weekly — if too many Drops, tighten filters in config  
5. Ignore ML predictions until ~100 eight-week outcomes  

## Config knobs (when quality feels off)

- `universe.min_avg_volume` / `min_market_cap_gbp` — fewer thin names  
- `scoring.conflict_penalty` — harder on daily-vs-weekly disagreement  
- Weights under `scoring:` — only after weeks of Keep/Drop + hit-rate data  

## Honest limits

No system removes market risk. This stack improves **selection discipline and feedback**, not a guaranteed edge.
