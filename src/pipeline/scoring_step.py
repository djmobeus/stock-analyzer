"""Phase 3 — scoring, ranking, and morning shortlist."""

from __future__ import annotations

import logging
from datetime import date

from analysis.scoring import market_regime_score, rank_candidates, score_stock
from config.loader import load_config
from data.fundamentals import snapshot_from_db
from db.repositories import upsert_candidates
from reports.morning_report import write_morning_report

logger = logging.getLogger(__name__)

_regime_cache: float | None = None


def _get_regime() -> float:
    global _regime_cache
    if _regime_cache is None:
        _regime_cache = market_regime_score()
    return _regime_cache


def score_universe(
    ticker_data: list[tuple[str, object]],
    briefing_for: str,
    universe_size: int,
    shadow_n: int = 15,
    shortlist_n: int = 10,
) -> dict:
    """Score all processed tickers, shadow-log top N, write morning shortlist."""
    config = load_config()
    weights = config.get("scoring", {})
    scores = []

    for ticker, daily_df in ticker_data:
        analyst = snapshot_from_db(ticker)
        s = score_stock(ticker, daily_df, analyst, weights)
        f = s.features
        f["market_regime_score"] = _get_regime()
        w = weights
        s.composite_score = round(
            w.get("support_proximity", 0.25) * f["support_score"]
            + w.get("multi_tf_confluence", 0.20) * (f["confluence"] / 3 * 100)
            + w.get("analyst_upside", 0.15) * f["analyst_upside_score"]
            + w.get("catalyst_proximity", 0.15) * f["catalyst_score"]
            + w.get("news_sentiment", 0.10) * f["news_sentiment_score"]
            + w.get("market_regime", 0.10) * f["market_regime_score"]
            + w.get("sector_relative", 0.05) * f["sector_relative_score"],
            2,
        )
        scores.append(s)

    shadow = rank_candidates(scores, top_n=shadow_n)
    shortlist = rank_candidates(scores, top_n=shortlist_n)

    upsert_candidates(date.today(), shadow)
    report_path = write_morning_report(shortlist, briefing_for, universe_size)

    logger.info(
        "Scoring: %d scored, %d shadow, %d shortlist",
        len(scores),
        len(shadow),
        len(shortlist),
    )
    for i, c in enumerate(shortlist[:5], 1):
        logger.info("  #%d %s score=%.1f", i, c.ticker, c.composite_score)

    return {
        "scored": len(scores),
        "shadow_logged": len(shadow),
        "shortlist": len(shortlist),
        "shortlist_scores": shortlist,
        "report_path": str(report_path),
        "top_ticker": shortlist[0].ticker if shortlist else None,
    }
