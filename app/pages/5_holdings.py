"""Holdings — Interactive Investor CSV import."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from data.ii_import import parse_ii_csv
from db.repositories import get_holdings, get_latest_price_gbx, upsert_holdings

bootstrap()

st.header("Holdings")
st.caption(
    "Import your Interactive Investor CSV (holdings export or account activity). "
    "Activity files net buys and sells automatically."
)

uploaded = st.file_uploader("Upload II CSV export", type=["csv"])
if uploaded:
    try:
        content = uploaded.getvalue()
        rows = parse_ii_csv(content)
        tickers = ", ".join(r.ticker for r in rows) or "—"
        st.info(
            f"Ready to import **{len(rows)}** open position(s): {tickers}. "
            "Sold positions (e.g. CHG) are excluded."
        )
        if st.button("Import holdings", type="primary"):
            n = upsert_holdings(rows)
            st.success(f"Saved {n} holdings.")
            st.rerun()
    except Exception as exc:
        st.error(str(exc))

holdings = get_holdings()
if not holdings:
    st.info("No holdings yet. Export CSV from Interactive Investor → Accounts → Export.")
    st.markdown("""
**How to export from Interactive Investor**
1. Log in to II → your account
2. Holdings → Export / Download (CSV)
3. Upload the file above
    """)
    st.stop()

st.subheader("Your holdings")
table = []
for h in holdings:
    latest = get_latest_price_gbx(h["ticker"])
    cost = h.get("avg_cost_gbx")
    qty = float(h.get("quantity") or 0)
    value = latest * qty if latest else None
    pnl_pct = None
    if latest and cost and cost > 0:
        pnl_pct = (latest - cost) / cost * 100
    table.append(
        {
            "Ticker": h["ticker"],
            "Name": h.get("name"),
            "Qty": qty,
            "Avg cost (p)": round(cost, 1) if cost else None,
            "Latest (p)": round(latest, 1) if latest else None,
            "P&L %": round(pnl_pct, 1) if pnl_pct is not None else None,
            "Value (p)": round(value, 0) if value else None,
        }
    )

st.dataframe(table, use_container_width=True, hide_index=True)
st.caption(
    f"Last import: {holdings[0].get('imported_at', '—')}. "
    "Latest prices come from the nightly scan database; tickers not in the scan may show blank."
)
