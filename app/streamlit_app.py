"""
UK Stock Analyzer — Streamlit dashboard entry point.

Deploy to Streamlit Community Cloud: set main file to app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="UK Stock Analyzer",
    page_icon="📈",
    layout="wide",
)

st.title("UK Stock Analyzer")
st.info(
    "Dashboard scaffold — implementation begins in Phase 4/6. "
    "See docs/tasks.md for the development roadmap."
)

st.markdown("""
### Planned views
- **Morning scan** — Top 5–10 ranked candidates
- **Portfolio** — Open observations and P&L
- **Patterns** — Hit rates and ML feature importance
- **Lookup** — Ad-hoc ticker analysis
""")
