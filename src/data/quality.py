"""Data quality checks and quarantine logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from data.prices import TickerPriceResult, latest_close_gbx


@dataclass
class QualityReport:
    """Quality assessment for one ticker."""

    ticker: str
    passed: bool
    flags: list[str] = field(default_factory=list)
    quarantine: bool = False
    quarantine_reason: str | None = None
    latest_close_gbx: float | None = None
    last_date: date | None = None


def _max_daily_jump_pct(df: pd.DataFrame) -> float:
    if "Close" not in df.columns or len(df) < 2:
        return 0.0
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return 0.0
    pct_changes = closes.pct_change().abs() * 100
    return float(pct_changes.max())


def _count_suspicious_jumps(df: pd.DataFrame, threshold_pct: float = 25.0) -> int:
    if "Close" not in df.columns or len(df) < 2:
        return 0
    closes = df["Close"].dropna()
    pct_changes = closes.pct_change().abs() * 100
    return int((pct_changes > threshold_pct).sum())


def check_price_quality(
    result: TickerPriceResult,
    max_daily_jump_pct: float = 25.0,
    stale_days: int = 5,
    min_price_gbx: float = 1.0,
    max_price_gbx: float = 500_000.0,
) -> QualityReport:
    """
    Run sanity checks on normalised price data.

    Returns a report; sets quarantine=True if data should not be used.
    """
    flags: list[str] = list(result.warnings)
    df = result.dataframe
    report = QualityReport(ticker=result.ticker, passed=True, flags=flags)

    if result.quarantine:
        report.passed = False
        report.quarantine = True
        report.quarantine_reason = result.quarantine_reason
        return report

    if df.empty:
        report.passed = False
        report.quarantine = True
        report.quarantine_reason = "empty_dataframe"
        return report

    report.latest_close_gbx = latest_close_gbx(result)
    last_ts = df.index.max()
    if hasattr(last_ts, "date"):
        report.last_date = last_ts.date()
    else:
        report.last_date = last_ts

    # Stale data
    if report.last_date:
        age = (date.today() - report.last_date).days
        if age > stale_days:
            flags.append(f"stale_data_{age}d")
            # Weekend: allow extra 2 days
            if age > stale_days + 2:
                report.quarantine = True
                report.quarantine_reason = f"stale_{age}d"

    # Price bounds
    close = report.latest_close_gbx
    if close is not None:
        if close < min_price_gbx:
            flags.append(f"price_below_min_{close:.2f}")
            report.quarantine = True
            report.quarantine_reason = "price_too_low"
        elif close > max_price_gbx:
            flags.append(f"price_above_max_{close:.2f}")
            report.quarantine = True
            report.quarantine_reason = "price_too_high"

    # Large daily jumps (possible 100x unit errors)
    jump_count = _count_suspicious_jumps(df, max_daily_jump_pct)
    if jump_count > 0:
        flags.append(f"large_jumps_{jump_count}")
    max_jump = _max_daily_jump_pct(df)
    if max_jump > 80:  # ~100% suggests unit flip
        report.quarantine = True
        report.quarantine_reason = f"max_jump_{max_jump:.0f}pct"

    # Zero volume on recent row
    if "Volume" in df.columns and len(df) > 0:
        recent_vol = df["Volume"].iloc[-5:]
        if (recent_vol == 0).all():
            flags.append("zero_volume_recent")

    report.flags = flags
    report.passed = not report.quarantine
    return report


def compare_with_reference(
    yahoo_close_gbx: float,
    reference_close_gbx: float,
    tolerance_pct: float = 2.0,
) -> tuple[bool, float]:
    """
  Compare Yahoo normalised price to a reference (e.g. Finnhub).

    Returns (within_tolerance, diff_pct).
    """
    if reference_close_gbx <= 0:
        return False, 100.0
    diff_pct = abs(yahoo_close_gbx - reference_close_gbx) / reference_close_gbx * 100
    return diff_pct <= tolerance_pct, diff_pct
