"""Tiered universe scanning — active (daily), watch (weekly), cold (monthly)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from config.loader import load_config
from data.fundamentals import AnalystSnapshot, is_trust_or_reit
from data.universe import StockRecord
from pipeline.calendar import _uk_now

logger = logging.getLogger(__name__)

TierName = Literal["active", "watch", "cold"]


def _uk_date(when: date | None = None) -> datetime:
    if when is None:
        return _uk_now()
    return _uk_now(datetime.combine(when, datetime.min.time()))


@dataclass
class ScanPlan:
    """Which tickers to refresh on this pipeline run."""

    tickers: list[str]
    bootstrap: bool
    watch_refresh: bool
    cold_refresh: bool
    priority_tickers: list[str]
    skipped_count: int


def _tier_cfg() -> dict:
    return load_config().get("universe_tiers", {})


def is_saturday_uk(when: date | None = None) -> bool:
    return _uk_date(when).weekday() == 5


def is_first_saturday_of_month_uk(when: date | None = None) -> bool:
    when_dt = _uk_date(when)
    return when_dt.weekday() == 5 and when_dt.day <= 7


def next_check_after(tier: TierName, today: date | None = None) -> date:
    """When this ticker should be checked again if it stays in the same tier."""
    today = today or date.today()
    cfg = _tier_cfg()

    if tier == "active":
        return today + timedelta(days=1)

    if tier == "watch":
        return today + timedelta(days=int(cfg.get("watch_recheck_days", 7)))

    return today + timedelta(days=int(cfg.get("cold_recheck_days", 30)))


def _parse_check_date(value: object | None) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _is_due(next_check: object | None, today: date) -> bool:
    check = _parse_check_date(next_check)
    return check is None or check <= today


def _liquidity_distance(
    rec: StockRecord,
    min_volume: float,
    min_cap: float,
    cfg: dict,
) -> tuple[TierName | None, str | None]:
    """Classify based on volume/cap only. None = passed liquidity."""
    vol = rec.avg_volume
    cap = rec.market_cap_gbp
    cold_vol = min_volume * float(cfg.get("cold_volume_ratio", 0.5))
    cold_cap = min_cap * float(cfg.get("cold_cap_ratio", 0.5))
    watch_vol = min_volume * float(cfg.get("watch_volume_ratio", 0.70))
    watch_cap = min_cap * float(cfg.get("watch_cap_ratio", 0.70))

    vol_fail = vol is not None and vol < min_volume
    cap_fail = cap is not None and cap < min_cap

    if vol is not None and vol < cold_vol:
        return "cold", "volume_far_below_min"
    if cap is not None and cap < cold_cap:
        return "cold", "market_cap_far_below_min"

    if vol_fail or cap_fail:
        near_vol = vol is not None and vol >= watch_vol
        near_cap = cap is not None and cap >= watch_cap
        if near_vol or near_cap:
            return "watch", "near_liquidity_threshold"
        if vol is None and cap is None:
            return "watch", "missing_liquidity_metrics"
        return "cold", "below_liquidity_threshold"

    return None, None


def classify_stock_tier(
    rec: StockRecord,
    snap: AnalystSnapshot | None,
    *,
    min_volume: float,
    min_cap: float,
    min_analysts: int,
) -> tuple[TierName, str]:
    """
    Assign active / watch / cold from metrics and optional analyst snapshot.

    Active = passes all universe filters today.
    """
    cfg = _tier_cfg()
    liq_tier, liq_reason = _liquidity_distance(rec, min_volume, min_cap, cfg)
    if liq_tier:
        return liq_tier, liq_reason or liq_tier

    if snap is None:
        return "cold", "no_analyst_data"

    if is_trust_or_reit(snap.name, snap.sector, snap.industry):
        return "cold", "trust_or_reit"

    if snap.analyst_count <= 0:
        return "cold", "no_analysts"

    if snap.analyst_count < min_analysts:
        return "watch", f"analyst_count_{snap.analyst_count}"

    if snap.fcf_improving is False:
        return "watch", "negative_fcf"

    return "active", "passes_filters"


def plan_daily_scan(
    all_tickers: list[str],
    tier_map: dict[str, dict],
    *,
    priority_tickers: list[str],
    today: date | None = None,
    bootstrap: bool = False,
) -> ScanPlan:
    """
    Choose tickers to metrics-check on this run.

    Daily: active tier + holdings + recent shadow candidates + new listings.
    Saturday: also re-check watch tier.
    First Saturday of month: also re-check cold tier.
    """
    today = today or date.today()
    watch_refresh = is_saturday_uk(today)
    cold_refresh = is_first_saturday_of_month_uk(today)

    if bootstrap:
        return ScanPlan(
            tickers=list(all_tickers),
            bootstrap=True,
            watch_refresh=watch_refresh,
            cold_refresh=cold_refresh,
            priority_tickers=list(priority_tickers),
            skipped_count=0,
        )

    scan: set[str] = set(priority_tickers)
    for ticker, row in tier_map.items():
        tier = row.get("tier", "cold")
        due = _is_due(row.get("next_check_after"), today)
        if tier == "active":
            scan.add(ticker)
        elif tier == "watch" and (due or watch_refresh):
            scan.add(ticker)
        elif tier == "cold" and (due or cold_refresh):
            scan.add(ticker)

    for ticker in all_tickers:
        if ticker not in tier_map:
            scan.add(ticker)

    scan.update(priority_tickers)
    ordered = [t for t in all_tickers if t in scan]
    skipped = len(all_tickers) - len(ordered)

    logger.info(
        "Scan plan: %d tickers to check (%d skipped). Watch refresh=%s, cold refresh=%s",
        len(ordered),
        skipped,
        watch_refresh,
        cold_refresh,
    )

    return ScanPlan(
        tickers=ordered,
        bootstrap=False,
        watch_refresh=watch_refresh,
        cold_refresh=cold_refresh,
        priority_tickers=list(priority_tickers),
        skipped_count=skipped,
    )


def passes_all_filters(
    rec: StockRecord,
    snap: AnalystSnapshot | None,
    *,
    min_volume: float,
    min_cap: float,
    min_analysts: int,
) -> bool:
    tier, _ = classify_stock_tier(
        rec,
        snap,
        min_volume=min_volume,
        min_cap=min_cap,
        min_analysts=min_analysts,
    )
    return tier == "active"
