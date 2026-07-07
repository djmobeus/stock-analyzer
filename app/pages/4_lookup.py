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
from visualization.charts import candlestick_chart

bootstrap()

st.header("Lookup")
st.caption("Analyse any LSE ticker and log an observation.")

ticker = st.text_input("Ticker", placeholder="e.g. PRU.L").strip().upper()
if ticker and not ticker.endswith(".L"):
    ticker = f"{ticker}.L"

if ticker:
    price = get_latest_price_gbx(ticker)
    snap = snapshot_from_db(ticker)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Latest close (p)", f"{price:.1f}" if price else "—")
    with col2:
        st.metric("Analyst target (p)", f"{snap.target_mean:.1f}" if snap and snap.target_mean else "—")
    with col3:
        st.metric("Analysts", snap.analyst_count if snap else "—")

    st.plotly_chart(candlestick_chart(ticker), use_container_width=True)

st.divider()
render_observation_form(default_ticker=ticker, key_prefix="lookup")

# Similar pattern preview when user types in sidebar session — show help text
st.subheader("Similar historical patterns")
st.caption("Enter a chart description in the form above to see matches after logging.")
