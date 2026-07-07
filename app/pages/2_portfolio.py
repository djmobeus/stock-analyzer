"""Portfolio — open observations and P&L."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from config.loader import load_config
from db.repositories import get_latest_price_gbx, get_observations, get_outcomes_for_observation

bootstrap()

st.header("Portfolio")
st.caption("Observations you have logged and their tracked outcomes.")

config = load_config()
target_pct = float(config.get("outcomes", {}).get("target_hit_pct", 8.0))
stop_pct = float(config.get("outcomes", {}).get("stop_loss_pct", -5.0))

observations = get_observations()
if not observations:
    st.info("No observations yet. Log one from Morning scan or Lookup.")
    st.stop()

alerts = []
rows = []
for obs in observations:
    ticker = obs["ticker"]
    entry = obs.get("entry_price_gbx")
    latest = get_latest_price_gbx(ticker)
    unrealized = None
    if entry and latest and float(entry) > 0:
        unrealized = (float(latest) - float(entry)) / float(entry) * 100
        if unrealized >= target_pct * 0.9:
            alerts.append(f"**{ticker}** near target ({unrealized:+.1f}%)")
        elif unrealized <= stop_pct * 0.9:
            alerts.append(f"**{ticker}** near stop ({unrealized:+.1f}%)")

    outcomes = get_outcomes_for_observation(int(obs["id"]))
    outcome_8w = next((o for o in outcomes if o["weeks"] == 8), None)

    rows.append(
        {
            "ID": obs["id"],
            "Ticker": ticker,
            "Logged": str(obs["observed_at"])[:10],
            "Prediction": obs["prediction"],
            "Confidence": obs["confidence"],
            "Entry (p)": round(float(entry), 1) if entry else None,
            "Latest (p)": round(latest, 1) if latest else None,
            "Unrealized %": round(unrealized, 1) if unrealized is not None else None,
            "8w %": outcome_8w["pct_change"] if outcome_8w else None,
            "8w target hit": outcome_8w["target_hit"] if outcome_8w else None,
        }
    )

if alerts:
    st.warning("Alerts: " + " · ".join(alerts))

st.dataframe(rows, use_container_width=True, hide_index=True)

st.subheader("Detail")
for obs in observations[:20]:
    obs_id = int(obs["id"])
    outcomes = get_outcomes_for_observation(obs_id)
    with st.expander(f"#{obs_id} {obs['ticker']} — {obs['prediction']} ({obs['confidence']})"):
        st.write(obs.get("chart_description") or "_No description_")
        if outcomes:
            st.table(
                [
                    {
                        "Weeks": o["weeks"],
                        "Price (p)": o["price_gbx"],
                        "Change %": o["pct_change"],
                        "Target hit": bool(o["target_hit"]),
                        "Stop hit": bool(o["stop_hit"]),
                    }
                    for o in outcomes
                ]
            )
        else:
            st.caption(f"Outcomes appear at 2, 4, and 8 weeks after {str(obs['observed_at'])[:10]}.")
