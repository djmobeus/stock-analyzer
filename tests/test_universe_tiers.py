"""Tests for tiered universe classification and scan planning."""

from datetime import date

from data.fundamentals import AnalystSnapshot
from data.universe import StockRecord
from pipeline.universe_tiers import (
    classify_stock_tier,
    next_check_after,
    plan_daily_scan,
    passes_all_filters,
)


def _snap(analyst_count: int = 5, fcf: bool | None = True) -> AnalystSnapshot:
    return AnalystSnapshot(
        ticker="TEST.L",
        target_mean=100.0,
        target_high=120.0,
        target_low=80.0,
        buy_count=3,
        hold_count=1,
        sell_count=0,
        analyst_count=analyst_count,
        fcf_improving=fcf,
        sector="Technology",
        name="Test PLC",
        industry="Software",
    )


def test_classify_active_passes_all_filters():
    rec = StockRecord("TEST.L", avg_volume=1_000_000, market_cap_gbp=500_000_000)
    tier, reason = classify_stock_tier(
        rec, _snap(), min_volume=500_000, min_cap=300_000_000, min_analysts=4
    )
    assert tier == "active"
    assert reason == "passes_filters"
    assert passes_all_filters(
        rec, _snap(), min_volume=500_000, min_cap=300_000_000, min_analysts=4
    )


def test_classify_cold_low_volume():
    rec = StockRecord("SMALL.L", avg_volume=100_000, market_cap_gbp=500_000_000)
    tier, reason = classify_stock_tier(
        rec, None, min_volume=500_000, min_cap=300_000_000, min_analysts=4
    )
    assert tier == "cold"
    assert "volume" in reason


def test_classify_watch_near_liquidity():
    rec = StockRecord("NEAR.L", avg_volume=400_000, market_cap_gbp=500_000_000)
    tier, reason = classify_stock_tier(
        rec, None, min_volume=500_000, min_cap=300_000_000, min_analysts=4
    )
    assert tier == "watch"
    assert reason == "near_liquidity_threshold"


def test_classify_watch_low_analyst_count():
    rec = StockRecord("TEST.L", avg_volume=1_000_000, market_cap_gbp=500_000_000)
    tier, reason = classify_stock_tier(
        rec, _snap(analyst_count=2), min_volume=500_000, min_cap=300_000_000, min_analysts=4
    )
    assert tier == "watch"
    assert reason == "analyst_count_2"


def test_plan_daily_scan_skips_cold_not_due():
    all_tickers = ["A.L", "B.L", "C.L"]
    tier_map = {
        "A.L": {"tier": "active", "next_check_after": "2026-07-10"},
        "B.L": {"tier": "watch", "next_check_after": "2026-07-20"},
        "C.L": {"tier": "cold", "next_check_after": "2026-08-01"},
    }
    plan = plan_daily_scan(
        all_tickers,
        tier_map,
        priority_tickers=[],
        today=date(2026, 7, 10),
        bootstrap=False,
    )
    assert plan.tickers == ["A.L"]
    assert plan.skipped_count == 2


def test_plan_daily_scan_includes_due_watch_and_cold():
    all_tickers = ["A.L", "B.L", "C.L"]
    tier_map = {
        "A.L": {"tier": "active", "next_check_after": "2026-07-10"},
        "B.L": {"tier": "watch", "next_check_after": "2026-07-09"},
        "C.L": {"tier": "cold", "next_check_after": "2026-07-01"},
    }
    plan = plan_daily_scan(
        all_tickers,
        tier_map,
        priority_tickers=[],
        today=date(2026, 7, 10),
    )
    assert set(plan.tickers) == {"A.L", "B.L", "C.L"}


def test_plan_includes_priority_and_new_listings():
    all_tickers = ["A.L", "NEW.L"]
    tier_map = {"A.L": {"tier": "cold", "next_check_after": "2026-08-01"}}
    plan = plan_daily_scan(
        all_tickers,
        tier_map,
        priority_tickers=["HOLD.L"],
        today=date(2026, 7, 10),
    )
    assert "HOLD.L" in plan.priority_tickers
    assert "NEW.L" in plan.tickers


def test_next_check_after_intervals():
    today = date(2026, 7, 10)
    assert next_check_after("active", today) == date(2026, 7, 11)
    assert next_check_after("watch", today) == date(2026, 7, 17)
    assert next_check_after("cold", today) == date(2026, 8, 9)
