"""Tests for support/resistance and composite scoring."""

from datetime import date

import numpy as np
import pandas as pd

from analysis.scoring import (
    analyst_upside_score,
    rank_candidates,
    score_stock,
    StockScore,
)
from analysis.support_resistance import (
    analyse_levels,
    distance_pct,
    pivot_points,
    support_proximity_score,
)
from data.fundamentals import AnalystSnapshot


def _sample_ohlcv(rows: int = 60, base: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range(end=date.today(), periods=rows, freq="B")
    close = base + np.sin(np.linspace(0, 4, rows)) * 5
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(rows, 1_000_000),
        },
        index=idx,
    )


def test_pivot_points():
    row = pd.Series({"High": 110, "Low": 90, "Close": 100})
    piv = pivot_points(row)
    assert piv["pivot"] == 100.0
    assert piv["s1"] < piv["pivot"]


def test_support_proximity_at_support():
    assert support_proximity_score(0.0) == 100.0
    assert support_proximity_score(3.0) == 0.0
    assert support_proximity_score(None) == 0.0


def test_distance_pct():
    assert distance_pct(100, 97) == 3.0


def test_analyse_levels_returns_scores():
    df = _sample_ohlcv()
    result = analyse_levels(df)
    assert "price_gbx" in result
    assert 0 <= result["support_score"] <= 100


def test_analyst_upside_score():
    snap = AnalystSnapshot(
        ticker="TEST.L",
        target_mean=120.0,
        target_high=130.0,
        target_low=110.0,
        buy_count=5,
        hold_count=2,
        sell_count=0,
        analyst_count=7,
    )
    assert analyst_upside_score(100.0, snap) == 66.66666666666666  # 20% upside vs 30% cap
    assert analyst_upside_score(100.0, None) == 0.0


def test_rank_candidates_deprioritises_conflict():
    high_conflict = StockScore("A.L", 80.0, conflict_flag=True)
    low_clean = StockScore("B.L", 75.0, conflict_flag=False)
    ranked = rank_candidates([high_conflict, low_clean], top_n=2)
    assert ranked[0].ticker == "B.L"


def test_score_stock_composite_in_range(monkeypatch):
    df = _sample_ohlcv()
    snap = AnalystSnapshot(
        ticker="TEST.L",
        target_mean=110.0,
        target_high=120.0,
        target_low=100.0,
        buy_count=4,
        hold_count=1,
        sell_count=0,
        analyst_count=5,
    )

    monkeypatch.setattr("analysis.scoring.confluence_score", lambda t, daily_close=None: (2, False))
    monkeypatch.setattr("analysis.scoring.catalyst_score", lambda t: 50.0)
    monkeypatch.setattr("analysis.scoring.news_sentiment_score", lambda t: 60.0)
    monkeypatch.setattr("analysis.scoring.market_regime_score", lambda: 100.0)
    monkeypatch.setattr("analysis.scoring._latest_indicator", lambda t, tf, name: 50.0)

    result = score_stock("TEST.L", df, snap)
    assert 0 <= result.composite_score <= 100
    assert result.ticker == "TEST.L"
