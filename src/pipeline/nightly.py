"""Nightly batch pipeline — universe, prices, indicators, scoring."""

from __future__ import annotations

import logging
import sys
from datetime import date

from analysis.indicators import compute_all_timeframes, indicators_to_rows
from config.loader import load_config, load_env
from data.prices import fetch_ohlcv
from data.quality import check_price_quality
from data.universe import build_filtered_universe, universe_as_of
from db.connection import init_database
from pipeline.calendar import next_briefing_day
from pipeline.delivery import deliver_morning_briefing
from pipeline.schedule_gate import should_run_scheduled_job
from pipeline.fundamentals_news import apply_phase2_filters, ingest_news_and_catalysts
from pipeline.outcomes import update_observation_outcomes
from pipeline.scoring_step import score_universe
from intelligence.ml_model import train_model
from db.repositories import count_outcomes_since_model_train
from db.repositories import (
    finish_scan_run,
    save_quality_flag,
    start_scan_run,
    upsert_daily_prices,
    upsert_indicators,
    upsert_stocks,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def process_ticker(ticker: str, dq_config: dict) -> tuple[bool, int, int, object | None]:
    """
    Fetch prices, quality-check, store prices and indicators.

    Returns (success, price_rows, indicator_rows, daily_dataframe_or_none).
    """
    result = fetch_ohlcv(ticker, period="2y")
    report = check_price_quality(
        result,
        max_daily_jump_pct=dq_config.get("max_daily_jump_pct", 25.0),
        stale_days=dq_config.get("stale_days", 5),
        min_price_gbx=dq_config.get("min_price_gbx", 1.0),
        max_price_gbx=dq_config.get("max_price_gbx", 500_000.0),
    )

    if report.quarantine:
        save_quality_flag(
            ticker=ticker,
            flag_date=date.today(),
            flag_type=report.quarantine_reason or "quarantine",
            details="; ".join(report.flags),
            quarantined=True,
        )
        logger.warning("%s quarantined: %s", ticker, report.quarantine_reason)
        return False, 0, 0, None

    price_rows = upsert_daily_prices(ticker, result.dataframe, result.currency)

    indicators = compute_all_timeframes(result.dataframe)
    ind_rows: list = []
    for tf, idf in indicators.items():
        ind_rows.extend(indicators_to_rows(ticker, idf, tf, latest_only=True))
    indicator_count = upsert_indicators(ind_rows)

    return True, price_rows, indicator_count, result.dataframe


def run_nightly_pipeline(limit: int | None = None, force: bool = False) -> dict:
    """Execute full nightly pipeline."""
    load_env()

    if not force:
        ok, gate_reason = should_run_scheduled_job(force=force)
        if not ok:
            logger.info("Pipeline skipped: %s", gate_reason)
            return {"status": "skipped", "reason": gate_reason}

    briefing = next_briefing_day()
    logger.info("Preparing morning briefing for: %s", briefing)

    config = load_config()
    dq_config = config.get("data_quality", {})

    init_database()
    run_id = start_scan_run()
    processed = 0
    quarantined = 0
    total_prices = 0
    total_indicators = 0
    ticker_data: list[tuple[str, object]] = []

    try:
        logger.info("Building filtered universe (filters 1–3)...")
        universe = build_filtered_universe(metrics_limit=limit)
        logger.info("After liquidity filters: %d stocks", len(universe))

        logger.info("Applying fundamental filters (4–6) via yfinance...")
        universe = apply_phase2_filters(universe)
        upsert_stocks(universe, universe_as_of())
        logger.info("Final universe size: %d stocks", len(universe))

        news_summary = ingest_news_and_catalysts(universe)

        outcome_summary = update_observation_outcomes()
        logger.info("Outcome tracking: %s", outcome_summary)

        ml_summary = {"ml_status": "skipped"}
        config_ml = config.get("ml", {})
        min_new = int(config_ml.get("retrain_min_new_outcomes", 5))
        if count_outcomes_since_model_train() >= min_new:
            ml_summary = train_model()
            logger.info("ML training: %s", ml_summary)

        for i, stock in enumerate(universe, 1):
            ticker = stock.ticker
            logger.info("[%d/%d] Processing %s", i, len(universe), ticker)
            try:
                ok, prices, indicators, df = process_ticker(ticker, dq_config)
                if ok and df is not None:
                    processed += 1
                    total_prices += prices
                    total_indicators += indicators
                    ticker_data.append((ticker, df))
                else:
                    quarantined += 1
            except Exception as exc:
                quarantined += 1
                logger.error("%s failed: %s", ticker, exc)
                save_quality_flag(
                    ticker=ticker,
                    flag_date=date.today(),
                    flag_type="pipeline_error",
                    details=str(exc),
                    quarantined=True,
                )

        scoring_summary = score_universe(
            ticker_data,
            briefing_for=briefing,
            universe_size=len(universe),
        )

        delivery_summary = deliver_morning_briefing(
            shortlist=scoring_summary.get("shortlist_scores", []),
            briefing_for=briefing,
            report_path=scoring_summary["report_path"],
            universe_size=len(universe),
        )
        scoring_log = {k: v for k, v in scoring_summary.items() if k != "shortlist_scores"}

        finish_scan_run(run_id, "success", processed, quarantined)
        summary = {
            "status": "success",
            "briefing_for": briefing,
            "universe_size": len(universe),
            "processed": processed,
            "quarantined": quarantined,
            "price_rows": total_prices,
            "indicator_rows": total_indicators,
            **news_summary,
            **outcome_summary,
            **ml_summary,
            **scoring_log,
            **delivery_summary,
        }
        logger.info("Pipeline complete: %s", summary)
        return summary

    except Exception as exc:
        finish_scan_run(run_id, "failed", processed, quarantined, str(exc))
        logger.exception("Pipeline failed")
        raise
