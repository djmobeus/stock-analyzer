"""Tiered FTSE universe build — daily active, weekly watch, monthly cold."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

from config.loader import load_config
from data.fundamentals import AnalystSnapshot, gather_analyst_snapshots
from data.universe import (
    StockRecord,
    apply_listing_filter,
    apply_volume_and_cap_filters,
    fetch_ftse_constituents,
    fetch_stock_metrics,
    load_exclusions,
)
from db.repositories import (
    count_universe_tiers,
    get_holdings_tickers,
    get_recent_shadow_tickers,
    get_universe_tiers_map,
    upsert_universe_tiers,
)
from pipeline.universe_tiers import (
    ScanPlan,
    classify_stock_tier,
    next_check_after,
    passes_all_filters,
    plan_daily_scan,
)

logger = logging.getLogger(__name__)


@dataclass
class TieredUniverseResult:
    """Output of a tiered universe refresh."""

    scorable: list[StockRecord]
    price_targets: list[StockRecord]
    scan_plan: ScanPlan
    stats: dict = field(default_factory=dict)


def _fetch_metrics_parallel(tickers: list[str], workers: int) -> list[StockRecord]:
    def _one(ticker: str) -> StockRecord:
        try:
            return fetch_stock_metrics(ticker)
        except Exception as exc:
            logger.warning("Failed metrics for %s: %s", ticker, exc)
            return StockRecord(ticker=ticker)

    records: list[StockRecord] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, t): t for t in tickers}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 25 == 0 or done == len(tickers):
                logger.info("Metrics progress: %d/%d", done, len(tickers))
            records.append(future.result())

    order = {t: i for i, t in enumerate(tickers)}
    records.sort(key=lambda r: order.get(r.ticker, 9999))
    return records


def _priority_tickers(tier_cfg: dict) -> list[str]:
    shadow_n = int(tier_cfg.get("shadow_priority_count", 15))
    holdings = get_holdings_tickers()
    shadow = get_recent_shadow_tickers(shadow_n)
    combined = list(dict.fromkeys([*holdings, *shadow]))
    return combined


def build_tiered_universe(metrics_limit: int | None = None) -> TieredUniverseResult:
    """
    Build today's scorable universe using tiered refresh rules.

    Falls back to full-universe scan when tiers are disabled, empty (bootstrap),
    or metrics_limit is set (testing).
    """
    config = load_config()
    universe_cfg = config.get("universe", {})
    tier_cfg = config.get("universe_tiers", {})
    pipeline_cfg = config.get("pipeline", {})
    min_vol = float(universe_cfg.get("min_avg_volume", 500_000))
    min_cap = float(universe_cfg.get("min_market_cap_gbp", 300_000_000))
    min_analysts = int(universe_cfg.get("min_analyst_count", 4))
    workers = int(pipeline_cfg.get("max_workers", 8))
    today = date.today()

    exclusions = load_exclusions()
    all_listed = apply_listing_filter(fetch_ftse_constituents(), exclusions)

    if metrics_limit:
        all_listed = all_listed[:metrics_limit]

    tiers_enabled = bool(tier_cfg.get("enabled", True)) and not metrics_limit
    bootstrap = tiers_enabled and count_universe_tiers() == 0
    tier_map = get_universe_tiers_map() if tiers_enabled else {}
    priority = _priority_tickers(tier_cfg) if tiers_enabled else []

    if tiers_enabled:
        scan_plan = plan_daily_scan(
            all_listed,
            tier_map,
            priority_tickers=priority,
            today=today,
            bootstrap=bootstrap,
        )
        tickers_to_check = scan_plan.tickers
    else:
        scan_plan = ScanPlan(
            tickers=all_listed,
            bootstrap=True,
            watch_refresh=False,
            cold_refresh=False,
            priority_tickers=[],
            skipped_count=0,
        )
        tickers_to_check = all_listed

    logger.info(
        "Tiered universe: checking %d/%d tickers (bootstrap=%s)",
        len(tickers_to_check),
        len(all_listed),
        scan_plan.bootstrap,
    )

    records = _fetch_metrics_parallel(tickers_to_check, workers)
    records_by_ticker = {r.ticker: r for r in records}

    liquidity_passed = apply_volume_and_cap_filters(records, min_vol, min_cap)
    snaps: dict[str, AnalystSnapshot | None] = gather_analyst_snapshots(liquidity_passed)

    tier_rows: list[tuple] = []
    tier_counts = {"active": 0, "watch": 0, "cold": 0}

    for rec in records:
        snap = snaps.get(rec.ticker)
        tier, reason = classify_stock_tier(
            rec,
            snap,
            min_volume=min_vol,
            min_cap=min_cap,
            min_analysts=min_analysts,
        )
        if rec.ticker in priority and tier == "cold":
            tier = "watch"
            reason = f"priority_override ({reason})"
        tier_counts[tier] += 1
        tier_rows.append(
            (
                rec.ticker,
                tier,
                reason,
                today.isoformat(),
                next_check_after(tier, today).isoformat(),
            )
        )

    if tiers_enabled:
        upsert_universe_tiers(tier_rows)

    scorable: list[StockRecord] = []
    for rec in liquidity_passed:
        snap = snaps.get(rec.ticker)
        if passes_all_filters(
            rec,
            snap,
            min_volume=min_vol,
            min_cap=min_cap,
            min_analysts=min_analysts,
        ):
            if snap and snap.name:
                rec.name = snap.name
            if snap and snap.sector:
                rec.sector = snap.sector
            scorable.append(rec)

    price_target_map = {r.ticker: r for r in scorable}
    for ticker in priority:
        rec = records_by_ticker.get(ticker)
        if rec and rec.ticker not in price_target_map:
            price_target_map[rec.ticker] = rec

    stats = {
        "tiers_enabled": tiers_enabled,
        "bootstrap": scan_plan.bootstrap,
        "constituents_total": len(all_listed),
        "tickers_checked": len(tickers_to_check),
        "tickers_skipped": scan_plan.skipped_count,
        "watch_refresh": scan_plan.watch_refresh,
        "cold_refresh": scan_plan.cold_refresh,
        "priority_tickers": len(priority),
        "liquidity_passed": len(liquidity_passed),
        "scorable": len(scorable),
        "tier_active": tier_counts["active"],
        "tier_watch": tier_counts["watch"],
        "tier_cold": tier_counts["cold"],
    }
    logger.info("Tier stats: %s", stats)

    return TieredUniverseResult(
        scorable=scorable,
        price_targets=list(price_target_map.values()),
        scan_plan=scan_plan,
        stats=stats,
    )
