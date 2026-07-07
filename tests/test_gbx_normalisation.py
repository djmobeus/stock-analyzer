"""Tests for GBX price normalisation."""

import pandas as pd

from data.prices import is_pence_currency, is_pound_currency, normalise_ohlcv_to_gbx


def test_pence_currency_detection():
    assert is_pence_currency("GBp") is True
    assert is_pence_currency("GBX") is True
    assert is_pound_currency("GBP") is True
    assert is_pound_currency("GBp") is False


def test_gbp_series_multiplied_to_gbx():
    df = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [10.5, 11.5],
            "Low": [9.5, 10.5],
            "Close": [10.0, 11.0],
            "Volume": [1000, 1100],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    out, warnings = normalise_ohlcv_to_gbx(df, "GBP", "TEST.L")
    assert "multiplying OHLC by 100" in warnings[0]
    assert out["Close"].iloc[0] == 1000.0
    assert out["Close"].iloc[1] == 1100.0


def test_gbp_pence_unchanged():
    df = pd.DataFrame(
        {"Close": [2500.0, 2550.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    out, warnings = normalise_ohlcv_to_gbx(df, "GBp", "TEST.L")
    assert out["Close"].iloc[0] == 2500.0
    assert not any("multiplying" in w for w in warnings)


def test_fix_pound_rows_in_pence_series():
    """Rows 100x too low should be corrected."""
    df = pd.DataFrame(
        {"Close": [2500.0, 2550.0, 25.50, 2600.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    out, warnings = normalise_ohlcv_to_gbx(df, "GBp", "TEST.L")
    assert any("100x too low" in w for w in warnings)
    assert out["Close"].iloc[2] == 2550.0  # 25.50 * 100
