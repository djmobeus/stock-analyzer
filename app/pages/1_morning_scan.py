"""Morning scan — top ranked candidates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from components.metrics_help import render_stock_score_breakdown, render_table_legend
from components.observation_form import render_observation_form
from db.repositories import get_candidates_for_scan, get_latest_candidate_scan
from intelligence.ml_model import predict_probability
from visualization.charts import TIMEFRAMES, candlestick_chart, investing_url

bootstrap()

st.header("Morning scan")
st.caption(
    "Today's **best matches** from the filtered universe — not a guarantee they will rise. "
    "Scores in the 50s often mean a quiet market day; we still show the top 10."
)

scan_date = get_latest_candidate_scan()
if not scan_date:
    st.warning("No scan results yet. Run the GitHub Actions pipeline first.")
    st.stop()

render_table_legend()

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
    ml_disp = f"{ml.probability}%" if ml.probability is not None else "Not yet"
    dist = features.get("distance_support_pct")
    conflict = features.get("conflict_flag")
    rows.append(
        {
            "Rank": c["rank"],
            "Ticker": c["ticker"],
            "Score /100": c["composite_score"],
            "ML prob 8%+": ml_disp,
            "Support dist %": round(dist, 1) if dist is not None else "—",
            "Timeframes agree": f"{features.get('confluence', 0)} of 3",
            "Timeframe conflict": "Yes — see detail" if conflict else "No",
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)

for c in candidates:
    ticker = c["ticker"]
    features = {}
    try:
        features = json.loads(c.get("features_json") or "{}")
    except json.JSONDecodeError:
        pass
    ml = predict_probability(features)
    conflict = features.get("conflict_flag")
    flag_note = " · ⚠ timeframe conflict" if conflict else ""

    with st.expander(
        f"#{c['rank']} {ticker} — score {c['composite_score']}{flag_note}"
    ):
        st.markdown(f"[Open on Investing.com ↗]({investing_url(ticker)})")

        render_stock_score_breakdown(features, float(c["composite_score"]))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Near support",
                f"{features.get('support_score', 0):.0f}/100",
                help="Higher = closer to a support level",
            )
            st.metric("Analyst target", f"{features.get('analyst_target', '—')}p")
        with col2:
            st.metric("Catalyst timing", f"{features.get('catalyst_score', 0):.0f}/100")
            if ml.probability is not None:
                st.metric("ML prob 8%+", f"{ml.probability}%")
            else:
                st.metric(
                    "ML prob 8%+",
                    "Not yet",
                    help="Needs ~100 completed 8-week outcomes",
                )
        with col3:
            st.metric("News mood", f"{features.get('news_sentiment_score', 0):.0f}/100")
            st.metric(
                "Timeframes agree",
                f"{features.get('confluence', 0)} of 3 daily/weekly/monthly",
            )

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
