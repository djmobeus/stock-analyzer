"""Chart helpers — OHLCV for TradingView Lightweight Charts + legacy Plotly."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from db.repositories import get_daily_prices_df
from visualization.links import research_links, yahoo_finance_url  # noqa: F401

TIMEFRAMES = {
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
}

_TF_RULE = {
    "Daily": None,
    "Weekly": "W-FRI",
    "Monthly": "ME",
}


def investing_url(ticker: str) -> str:
    """Backward-compatible: primary research URL (Yahoo if no Investing slug)."""
    return research_links(ticker)["primary"]


def _resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample daily OHLCV to weekly/monthly bars."""
    if df is None or df.empty:
        return pd.DataFrame()
    rule = _TF_RULE.get(timeframe)
    if not rule:
        return df
    agg = df.resample(rule).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    return agg.dropna(subset=["Open", "High", "Low", "Close"])


def _bars_to_candles(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ts, row in df.iterrows():
        d = ts.date() if hasattr(ts, "date") else pd.Timestamp(ts).date()
        rows.append(
            {
                "time": d.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            }
        )
    rows.sort(key=lambda r: r["time"])
    return rows


def _bars_to_volume(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ts, row in df.iterrows():
        d = ts.date() if hasattr(ts, "date") else pd.Timestamp(ts).date()
        rows.append({"time": d.isoformat(), "value": float(row.get("Volume") or 0)})
    rows.sort(key=lambda r: r["time"])
    return rows


def ohlcv_for_lightweight(
    ticker: str, limit: int = 520, timeframe: str = "Daily"
) -> list[dict[str, Any]]:
    """JSON-serialisable candles for Lightweight Charts."""
    df = get_daily_prices_df(ticker, limit=limit)
    df = _resample_ohlcv(df, timeframe)
    if df is None or df.empty:
        return []
    return _bars_to_candles(df)


def volume_for_lightweight(
    ticker: str, limit: int = 520, timeframe: str = "Daily"
) -> list[dict[str, Any]]:
    df = get_daily_prices_df(ticker, limit=limit)
    df = _resample_ohlcv(df, timeframe)
    if df is None or df.empty:
        return []
    return _bars_to_volume(df)


def chart_series(
    ticker: str, timeframe: str = "Daily", limit: int = 520
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Candles + volume for one timeframe."""
    tf = timeframe if timeframe in TIMEFRAMES else "Daily"
    return (
        ohlcv_for_lightweight(ticker, limit=limit, timeframe=tf),
        volume_for_lightweight(ticker, limit=limit, timeframe=tf),
    )


def score_breakdown_rows(features: dict, weights: dict | None = None) -> list[dict]:
    """Plain-English score component rows for the stock detail page."""
    from config.loader import load_config

    w = weights or load_config().get("scoring", {})
    conf = float(features.get("confluence") or 0)
    conf_score = conf / 3 * 100
    components = [
        ("Near support", "support_proximity", features.get("support_score"), "support_score"),
        ("Timeframes agree", "multi_tf_confluence", conf_score, "confluence"),
        ("Analyst upside", "analyst_upside", features.get("analyst_upside_score"), "analyst_upside_score"),
        ("Catalyst timing", "catalyst_proximity", features.get("catalyst_score"), "catalyst_score"),
        ("News mood", "news_sentiment", features.get("news_sentiment_score"), "news_sentiment_score"),
        ("Market regime", "market_regime", features.get("market_regime_score"), "market_regime_score"),
        ("Sector relative", "sector_relative", features.get("sector_relative_score"), "sector_relative_score"),
    ]
    rows = []
    for label, wkey, value, _fkey in components:
        weight = float(w.get(wkey, 0) or 0)
        val = float(value) if value is not None else None
        contrib = round(weight * val, 1) if val is not None else None
        rows.append(
            {
                "label": label,
                "weight_pct": round(weight * 100),
                "score": round(val, 1) if val is not None else None,
                "contribution": contrib,
            }
        )
    return rows


def candlestick_chart(ticker: str, timeframe: str = "Daily"):
    """Legacy Plotly chart (Streamlit). Prefer Lightweight Charts in webapp."""
    df = get_daily_prices_df(ticker, limit=520)
    df = _resample_ohlcv(df, timeframe)
    fig = go.Figure()
    if df is None or df.empty:
        fig.update_layout(title=f"{ticker} — no price data", height=420)
        return fig
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
        )
    )
    fig.update_layout(
        title=f"{ticker} ({timeframe}) — Yahoo/yfinance GBX",
        xaxis_rangeslider_visible=False,
        height=480,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


__all__ = [
    "TIMEFRAMES",
    "investing_url",
    "yahoo_finance_url",
    "candlestick_chart",
    "ohlcv_for_lightweight",
    "volume_for_lightweight",
    "chart_series",
    "score_breakdown_rows",
    "research_links",
]
