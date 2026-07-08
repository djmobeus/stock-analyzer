"""Morning scan — top ranked candidates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from components.observation_form import render_observation_form
from db.repositories import get_candidates_for_scan, get_latest_candidate_scan
from intelligence.ml_model import predict_probability
from visualization.charts import TIMEFRAMES, candlestick_chart, investing_url

bootstrap()

st.header("Morning scan")
st.caption(
    "Top 10 from the latest nightly run (shadow log keeps top 15). "
    "Score is a weighted composite out of 100 — not financial advice."
)

scan_date = get_latest_candidate_scan()
if not scan_date:
    st.warning("No scan results yet. Run the GitHub Actions pipeline first.")
    st.stop()

candidates = get_candidates_for_scan(scan_date, limit=10)
st.subheader(f"Scan date: {scan_date.isoformat()}")

rows = []
for c in candidates:
    features = {}
    try:
        features = json.loads(c.get("features_json") or "{}")
    except json.JSONDecodeError:
        pass
    ml = predict_probability(features)
    ml_disp = f"{ml.probability}%" if ml.probability is not None else "—"
    dist = features.get("distance_support_pct")
    rows.append(
        {
            "Rank": c["rank"],
            "Ticker": c["ticker"],
            "Score /100": c["composite_score"],
            "ML %": ml_disp,
            "Support dist %": round(dist, 1) if dist is not None else "—",
            "Confluence": f"{features.get('confluence', 0)}/3",
            "Flags": "MTF conflict" if features.get("conflict_flag") else "—",
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)
st.caption(
    "**Score** = weighted mix of support, confluence, analyst upside, catalysts, sentiment, regime "
    "(max ~100). **ML %** unlocks after ~100 labelled 8-week outcomes. "
    "**Support dist %** = distance of price from nearest support. "
    "**Confluence** = how many of daily/weekly/monthly look bullish (0–3). "
    "**MTF conflict** = daily bullish while weekly or monthly is not."
)

for c in candidates:
    ticker = c["ticker"]
    features = {}
    try:
        features = json.loads(c.get("features_json") or "{}")
    except json.JSONDecodeError:
        pass
    ml = predict_probability(features)

    with st.expander(f"#{c['rank']} {ticker} — score {c['composite_score']}"):
        st.markdown(f"[Open on Investing.com ↗]({investing_url(ticker)})")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Support score", f"{features.get('support_score', 0):.0f}")
            st.metric("Analyst target", f"{features.get('analyst_target', '—')}p")
        with col2:
            st.metric("Catalyst score", f"{features.get('catalyst_score', 0):.0f}")
            if ml.probability is not None:
                st.metric("ML P(hit)", f"{ml.probability}%")
            else:
                st.metric("ML P(hit)", "N/A", help="Needs 100+ labelled 8-week outcomes")
        with col3:
            st.metric("News sentiment", f"{features.get('news_sentiment_score', 0):.0f}")
            if features.get("conflict_flag"):
                st.warning("Multi-timeframe conflict")

        tf = st.radio(
            "Chart timeframe",
            list(TIMEFRAMES.keys()),
            horizontal=True,
            key=f"tf_{ticker}",
        )
        st.plotly_chart(
            candlestick_chart(ticker, timeframe=tf),
            use_container_width=True,
        )
        render_observation_form(default_ticker=ticker, key_prefix=f"scan_{ticker}")
