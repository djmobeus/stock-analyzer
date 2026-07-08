"""Ticker lookup and observation logging."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from components.observation_form import render_observation_form
from data.fundamentals import snapshot_from_db
from db.repositories import get_latest_price_gbx
from visualization.charts import TIMEFRAMES, candlestick_chart, investing_url

bootstrap()

st.header("Lookup")
st.caption("Analyse any LSE ticker and log an observation — even if it’s not on the shortlist.")

ticker = st.text_input("Ticker", placeholder="e.g. PRU.L").strip().upper()
if ticker and not ticker.endswith(".L"):
    ticker = f"{ticker}.L"

if ticker:
    st.markdown(f"[Open on Investing.com ↗]({investing_url(ticker)})")
    price = get_latest_price_gbx(ticker)
    snap = snapshot_from_db(ticker)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Latest close (p)", f"{price:.1f}" if price else "—")
    with col2:
        st.metric(
            "Analyst target (p)",
            f"{snap.target_mean:.1f}" if snap and snap.target_mean else "—",
        )
    with col3:
        st.metric("Analysts", snap.analyst_count if snap else "—")

    tf = st.radio(
        "Chart timeframe",
        list(TIMEFRAMES.keys()),
        horizontal=True,
        key=f"lookup_tf_{ticker}",
    )
    st.plotly_chart(candlestick_chart(ticker, timeframe=tf), use_container_width=True)

st.divider()
render_observation_form(default_ticker=ticker, key_prefix="lookup")
