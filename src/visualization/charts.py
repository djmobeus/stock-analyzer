"""Plotly chart helpers for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.prices import fetch_ohlcv
from db.repositories import get_daily_prices_df


def load_chart_df(ticker: str, days: int = 180) -> pd.DataFrame:
    """OHLCV for charts — DB first, yfinance fallback."""
    df = get_daily_prices_df(ticker, limit=days)
    if not df.empty:
        return df
    result = fetch_ohlcv(ticker, period="6mo")
    if result.dataframe.empty:
        return pd.DataFrame()
    out = result.dataframe.copy()
    out = out.rename(
        columns={
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
        }
    )
    return out[["Open", "High", "Low", "Close", "Volume"]]


def candlestick_chart(ticker: str, df: pd.DataFrame | None = None, title: str | None = None) -> go.Figure:
    """Daily candlestick with volume subplot."""
    if df is None:
        df = load_chart_df(ticker)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker} — no price data", height=400)
        return fig

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name=ticker,
            )
        ]
    )
    fig.update_layout(
        title=title or f"{ticker} — daily",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white",
    )
    return fig
