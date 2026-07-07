"""Technical indicator calculations (pure pandas — no pandas-ta dependency)."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TIMEFRAMES = ("daily", "weekly", "monthly")


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample daily OHLCV to weekly or monthly."""
    if df.empty:
        return df
    ohlcv = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    if timeframe == "daily":
        return ohlcv
    rule = "W-FRI" if timeframe == "weekly" else "ME"
    resampled = ohlcv.resample(rule).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    ).dropna(subset=["Close"])
    return resampled


def _sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd_line = ema12 - ema26
    signal = _ema(macd_line, 9)
    hist = macd_line - signal
    return macd_line, signal, hist


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to an OHLCV dataframe."""
    if df.empty or len(df) < 30:
        return df

    out = df.copy()
    out["sma_20"] = _sma(out["Close"], 20)
    out["sma_50"] = _sma(out["Close"], 50)
    out["sma_200"] = _sma(out["Close"], 200)
    out["rsi_14"] = _rsi(out["Close"], 14)

    macd_line, signal, hist = _macd(out["Close"])
    out["macd"] = macd_line
    out["macd_signal"] = signal
    out["macd_hist"] = hist

    out["obv"] = _obv(out["Close"], out["Volume"])
    out["golden_cross"] = (out["sma_50"] > out["sma_200"]).astype(int)

    return out


def indicators_to_rows(
    ticker: str,
    df: pd.DataFrame,
    timeframe: str,
    latest_only: bool = False,
) -> list[dict[str, Any]]:
    """Flatten indicator dataframe to list of DB row dicts."""
    indicator_cols = [
        c for c in df.columns
        if c not in ("Open", "High", "Low", "Close", "Volume", "Adj Close")
    ]
    rows: list[dict[str, Any]] = []
    if df.empty:
        return rows

    # Nightly pipeline stores latest snapshot only (faster; full history from daily_prices)
    iter_rows = [df.iloc[-1]] if latest_only else [row for _, row in df.iterrows()]

    for row in iter_rows:
        ts = row.name if hasattr(row, "name") else df.index[-1]
        d = ts.date() if hasattr(ts, "date") else ts
        for col in indicator_cols:
            val = row.get(col)
            if pd.isna(val):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "date": d,
                    "timeframe": timeframe,
                    "indicator_name": col.lower(),
                    "value": float(val),
                    "metadata": None,
                }
            )
    return rows


def compute_all_timeframes(daily_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Calculate indicators on daily, weekly, and monthly resampled data."""
    result: dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        resampled = resample_ohlcv(daily_df, tf)
        result[tf] = calculate_indicators(resampled)
    return result
