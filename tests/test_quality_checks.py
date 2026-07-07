"""Tests for price quality checks."""

import pandas as pd

from data.prices import TickerPriceResult
from data.quality import check_price_quality, compare_with_reference


def _make_result(closes: list[float], ticker: str = "TEST.L") -> TickerPriceResult:
    df = pd.DataFrame(
        {"Close": closes, "Volume": [1_000_000] * len(closes)},
        index=pd.date_range("2024-06-01", periods=len(closes), freq="D"),
    )
    return TickerPriceResult(ticker=ticker, currency="GBp", dataframe=df)


def test_compare_within_tolerance():
    ok, diff = compare_with_reference(1000.0, 1010.0, tolerance_pct=2.0)
    assert ok is True
    assert diff < 2.0


def test_compare_outside_tolerance():
    ok, diff = compare_with_reference(1000.0, 1100.0, tolerance_pct=2.0)
    assert ok is False
    assert diff > 2.0


def test_quarantine_on_extreme_jump():
    # Simulate 100x unit error day
    closes = [2500.0] * 10 + [25.0] + [2600.0] * 5
    result = _make_result(closes)
    report = check_price_quality(result, stale_days=30)
    assert report.quarantine or "large_jumps" in " ".join(report.flags)
