"""Pattern statistics — rolling hit rates by setup type."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from _bootstrap import bootstrap
from config.loader import load_config
from db.repositories import get_pattern_stats
from intelligence.ml_model import get_feature_importance

bootstrap()

st.header("Patterns")
st.caption("Hit rates by chart setup type and ML feature importance.")

config = load_config()
min_per_pattern = 30

stats = get_pattern_stats()
if stats:
    rows = []
    for s in stats:
        sample = int(s["sample_count"] or 0)
        hits = int(s["hit_count"] or 0)
        hit_rate = hits / sample * 100 if sample else 0
        rows.append(
            {
                "Pattern": s["pattern_type"],
                "Samples": sample,
                "Hits": hits,
                "Hit rate %": round(hit_rate, 1),
                "Avg gain %": s["avg_gain_pct"],
                "Reliable": "✓" if sample >= min_per_pattern else f"need {min_per_pattern - sample}",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.info("No pattern statistics yet — log observations with chart descriptions.")

st.subheader("ML feature importance")
imp = get_feature_importance()
ml_cfg = config.get("ml", {})
if imp:
    st.bar_chart(imp)
else:
    st.caption(
        f"Feature importance appears after ML training "
        f"({ml_cfg.get('min_samples_logistic', 100)}+ labelled 8-week outcomes)."
    )

st.markdown("""
**Pattern detection** — chart descriptions are tagged automatically
(e.g. `support_bounce`, `golden_cross`, `catalyst`).
Multiple tags combine into one pattern key for statistics.
""")
