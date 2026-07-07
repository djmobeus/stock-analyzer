"""Reusable observation logging form."""

from __future__ import annotations

import streamlit as st

from db.repositories import get_observations_with_outcomes
from intelligence.patterns import find_similar_observations, format_similar_summary
from observations.service import log_observation


def render_observation_form(default_ticker: str = "", key_prefix: str = "obs") -> None:
    """Render and handle observation log form."""
    with st.form(f"{key_prefix}_form"):
        ticker = st.text_input("Ticker", value=default_ticker, placeholder="e.g. AAF.L")
        col1, col2 = st.columns(2)
        with col1:
            prediction = st.selectbox("Prediction", ["buy", "watch", "avoid"])
        with col2:
            confidence = st.selectbox("Confidence", ["low", "medium", "high"])
        entry = st.number_input(
            "Entry price (pence)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            help="Leave at 0 to use the latest closing price from the database.",
        )
        desc = st.text_area(
            "Chart description",
            placeholder="e.g. bounce off support near 200 SMA, catalyst in 3 weeks...",
            height=100,
        )
        submitted = st.form_submit_button("Log observation", type="primary")

    if submitted:
        if not ticker.strip():
            st.error("Please enter a ticker.")
            return
        try:
            entry_price = entry if entry > 0 else None
            obs_id = log_observation(
                ticker=ticker,
                prediction=prediction,
                confidence=confidence,
                chart_description=desc,
                entry_price_gbx=entry_price,
            )
            st.success(f"Logged observation #{obs_id} for {ticker.strip().upper()}")
            if desc.strip():
                similar = find_similar_observations(desc, get_observations_with_outcomes())
                summary = format_similar_summary(similar)
                if summary:
                    st.info(summary)
        except Exception as exc:
            st.error(str(exc))
