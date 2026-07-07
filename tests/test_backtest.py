"""Tests for backtest module."""

from datetime import date

from analysis.backtest import BacktestSummary, BacktestTrade, run_backtest


def test_backtest_empty_db(monkeypatch):
    monkeypatch.setattr("analysis.backtest._load_historical_candidates", lambda: [])
    summary = run_backtest()
    assert summary.sample_count == 0
    assert summary.hit_rate_pct == 0.0


def test_backtest_summary_dataclass():
    t = BacktestTrade(
        ticker="TEST.L",
        scan_date=date(2026, 1, 1),
        rank=1,
        composite_score=75.0,
        entry_gbx=100.0,
        exit_gbx=110.0,
        pct_change=10.0,
        target_hit=True,
        stop_hit=False,
    )
    s = BacktestSummary(trades=[t], hit_rate_pct=100.0, avg_return_pct=10.0, sample_count=1)
    assert s.sample_count == 1
