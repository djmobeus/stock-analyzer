"""Tests for indicator calculations."""

import pandas as pd
import numpy as np

from analysis.indicators import calculate_indicators, indicators_to_rows, resample_ohlcv


def _sample_ohlcv(n: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 1000 + np.cumsum(np.random.randn(n) * 5)
    return pd.DataFrame(
        {
            "Open": close - 2,
            "High": close + 5,
            "Low": close - 5,
            "Close": close,
            "Volume": np.random.randint(500_000, 2_000_000, n),
        },
        index=idx,
    )


def test_calculate_indicators_adds_columns():
    df = _sample_ohlcv(100)
    result = calculate_indicators(df)
    assert "rsi_14" in result.columns
    assert "sma_50" in result.columns
    assert "macd" in result.columns


def test_latest_only_rows():
    df = calculate_indicators(_sample_ohlcv(100))
    rows = indicators_to_rows("TEST.L", df, "daily", latest_only=True)
    names = {r["indicator_name"] for r in rows}
    assert "rsi_14" in names
    assert len(rows) <= 15  # one snapshot, not full history
