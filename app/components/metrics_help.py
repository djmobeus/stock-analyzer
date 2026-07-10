"""Plain-English help text and score breakdown for the dashboard."""

from __future__ import annotations

import streamlit as st

from config.loader import load_config

SCORE_GUIDE = """
**What the score means (0–100)**

The score is **not** “this stock will definitely go up.” It means: *how well this stock matches the rules we care about today* — near support, timeframe agreement, analyst upside, catalysts, news, and the wider market.

- **50–60** — Moderate match. Common on quiet days. These are the **best of what passed filters today**, not guaranteed winners.
- **60–75** — Stronger setup.
- **75+** — Rare; several factors lining up well.

A score of **53 vs 55** is a small difference — rank order matters more than the exact number.
"""

ML_GUIDE = """
**ML prob 8%+** — *Machine learning probability (when available)*

This will estimate the chance of a **+8% gain within 8 weeks** (your typical target).

Shows **—** until the system has **~100 completed 8-week outcomes** from nightly shadow logging and your observations. Until then, rely on the **Score** column.
"""

CONFLUENCE_GUIDE = """
**Timeframes agree (0–3)**

We check three charts: **daily**, **weekly**, and **monthly**.

For each, we ask: is price above the 50-day average and RSI not overbought?

- **0/3** — None look bullish on those rules  
- **2/3** — Two agree (often daily + weekly)  
- **3/3** — All three agree — stronger alignment  

Higher is usually better for your style of trading with the trend.
"""

CONFLICT_GUIDE = """
**Timeframe conflict**

The **daily** chart looks bullish, but the **weekly** and/or **monthly** chart does **not**.

That is a caution flag — short-term strength vs longer-term weakness. Not a ban — worth checking the weekly/monthly chart before acting.
"""

SUPPORT_GUIDE = """
**Support distance %**

How far the current price is from the nearest **support** level (a price area where the stock has bounced before).

**Smaller %** = closer to support (often what you want for a bounce trade).
"""

ANTHROPIC_GUIDE = """
### Morning email summary (Anthropic / Claude Haiku)

**What it is:** A short plain-English paragraph at the top of your morning email, written by AI from the same numbers in the table.

**What it is not:** A buy/sell instruction. The rules and scores do the real work.

**Cost:** About **1–3 pence per morning** from your $5 credit (~£3–5/month at most).

**How to know it ran:**
1. Email has a **“Morning summary”** section with flowing sentences (not just a bullet list).
2. Home page **Anthropic usage** shows a tiny amount after a run (may take a reboot to refresh).

**If usage stays $0:** The free template was used instead — check `ANTHROPIC_API_KEY` is set in **GitHub Actions secrets** (not only local `.env`).

**Spending limit:** [console.anthropic.com](https://console.anthropic.com) → Settings → Limits.
"""


def score_breakdown_rows(features: dict) -> list[dict]:
    """Per-component score and weighted contribution (approx)."""
    w = load_config().get("scoring", {})
    conf = features.get("confluence", 0) or 0
    conf_score = conf / 3 * 100

    parts = [
        ("Near support", features.get("support_score", 0) or 0, w.get("support_proximity", 0.25)),
        ("Timeframes agree", conf_score, w.get("multi_tf_confluence", 0.20)),
        ("Analyst upside", features.get("analyst_upside_score", 0) or 0, w.get("analyst_upside", 0.15)),
        ("Catalyst timing", features.get("catalyst_score", 0) or 0, w.get("catalyst_proximity", 0.15)),
        ("News mood", features.get("news_sentiment_score", 0) or 0, w.get("news_sentiment", 0.10)),
        ("Market (FTSE)", features.get("market_regime_score", 0) or 0, w.get("market_regime", 0.10)),
        ("Sector vs market", features.get("sector_relative_score", 0) or 0, w.get("sector_relative", 0.05)),
    ]
    rows = []
    for label, subscore, weight in parts:
        subscore = float(subscore)
        weight = float(weight)
        rows.append(
            {
                "Factor": label,
                "Sub-score (/100)": round(subscore, 1),
                "Weight": f"{weight * 100:.0f}%",
                "Adds to total": round(subscore * weight, 1),
            }
        )
    return rows


def render_table_legend() -> None:
    """Collapsible guide above the candidates table."""
    with st.expander("How to read this table (tap to open)", expanded=False):
        st.markdown(SCORE_GUIDE)
        st.markdown("---")
        st.markdown("**Column guide**")
        st.markdown(
            "- **Score /100** — Weighted mix of the factors in the breakdown below (max 100).\n"
            "- **ML prob 8%+** — Estimated chance of +8% within 8 weeks (after ~100 outcomes).\n"
            "- **Support dist %** — How far price is from the nearest support level.\n"
            "- **Timeframes agree** — How many of daily / weekly / monthly look bullish (0–3).\n"
            "- **Timeframe conflict** — Daily bullish but weekly or monthly is not."
        )
        with st.expander("More on confluence / timeframes"):
            st.markdown(CONFLUENCE_GUIDE)
            st.markdown(CONFLICT_GUIDE)


def render_stock_score_breakdown(features: dict, composite: float) -> None:
    """Show breakdown table for one stock."""
    st.markdown(f"**Score breakdown** (total **{composite:.1f}** / 100)")
    rows = score_breakdown_rows(features)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if features.get("conflict_flag"):
        st.warning(
            "**Timeframe conflict:** The daily chart looks bullish, but the weekly "
            "and/or monthly chart does not. Check the Weekly and Monthly chart buttons above."
        )
