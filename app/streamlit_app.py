"""
UK Stock Analyzer — Streamlit dashboard entry point.

Deploy to Streamlit Community Cloud: set main file to app/streamlit_app.py
"""

import streamlit as st

from _bootstrap import bootstrap
from config.loader import load_config
from db.repositories import get_latest_candidate_scan, get_scan_summary
from intelligence.ml_model import get_feature_importance, load_model_bundle

bootstrap()

st.set_page_config(
    page_title="UK Stock Analyzer",
    page_icon="📈",
    layout="wide",
)

st.title("UK Stock Analyzer")
st.caption("Analytical screening for FTSE 100/250 — not financial advice.")

summary = get_scan_summary()
config = load_config()
ml_cfg = config.get("ml", {})
bundle = load_model_bundle()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Latest scan", summary.get("latest_scan_date") or "—")
with col2:
    st.metric("Last run", summary.get("last_run_status") or "—")
with col3:
    st.metric("Observations", summary.get("observation_count", 0))
with col4:
    st.metric("8w outcomes", summary.get("outcome_8w_count", 0))

if bundle:
    st.success(
        f"ML model **{bundle.version}** active "
        f"({bundle.sample_count} samples, CV {bundle.cv_score:.1%})"
    )
else:
    need = ml_cfg.get("min_samples_logistic", 100)
    have = summary.get("outcome_8w_count", 0)
    st.info(f"ML predictions unlock at {need} labelled outcomes ({have}/{need} so far).")

st.markdown("""
### Navigate
| Page | Purpose |
|------|---------|
| **Morning scan** | Ranked candidates, charts, ML probability |
| **Portfolio** | Your observations, P&L, outcome tracking |
| **Patterns** | Hit rates and feature importance |
| **Lookup** | Any ticker + candlestick chart |
| **Holdings** | Import Interactive Investor CSV, portfolio P&L |
""")

if summary.get("finished_at"):
    st.caption(f"Last pipeline finished: {summary['finished_at']}")

imp = get_feature_importance()
if imp:
    with st.expander("Top ML features (latest model)"):
        st.bar_chart(imp)
