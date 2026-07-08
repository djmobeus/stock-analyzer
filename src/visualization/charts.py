"""Plotly chart helpers for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.prices import fetch_ohlcv
from db.repositories import get_daily_prices_df

TIMEFRAMES = {
    "Daily": ("D", 180),
    "Weekly": ("W", 520),
    "Monthly": ("ME", 1500),
}


def load_chart_df(ticker: str, days: int = 180) -> pd.DataFrame:
    """OHLCV for charts — DB first, yfinance fallback."""
    df = get_daily_prices_df(ticker, limit=days)
    if not df.empty:
        return df
    result = fetch_ohlcv(ticker, period="2y" if days > 400 else "6mo")
    if result.dataframe.empty:
        return pd.DataFrame()
    out = result.dataframe.copy()
    cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in out.columns]
    return out[cols]


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "D" or df.empty:
        return df
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in df.columns:
        agg["Volume"] = "sum"
    return df.resample(rule).agg(agg).dropna(subset=["Close"])


def candlestick_chart(
    ticker: str,
    df: pd.DataFrame | None = None,
    title: str | None = None,
    timeframe: str = "Daily",
) -> go.Figure:
    """Candlestick chart for daily / weekly / monthly."""
    rule, lookback = TIMEFRAMES.get(timeframe, ("D", 180))
    if df is None:
        df = load_chart_df(ticker, days=lookback)
    else:
        df = df.tail(lookback) if len(df) > lookback else df

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker} — no price data", height=400)
        return fig

    plot_df = _resample_ohlcv(df, rule)
    if plot_df.empty:
        plot_df = df

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=plot_df.index,
                open=plot_df["Open"],
                high=plot_df["High"],
                low=plot_df["Low"],
                close=plot_df["Close"],
                name=ticker,
            )
        ]
    )
    fig.update_layout(
        title=title or f"{ticker} — {timeframe.lower()}",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white",
    )
    return fig


def investing_url(ticker: str) -> str:
    """Search link on Investing.com for an LSE ticker."""
    epic = ticker.replace(".L", "").replace(".l", "")
    return f"https://www.investing.com/search/?q={epic}"
