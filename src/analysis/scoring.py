"""Composite scoring and multi-timeframe confluence."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from analysis.support_resistance import analyse_levels
from config.loader import load_config
from data.fundamentals import AnalystSnapshot
from db.connection import get_connection, get_placeholder

logger = logging.getLogger(__name__)


@dataclass
class StockScore:
    ticker: str
    composite_score: float
    features: dict = field(default_factory=dict)
    conflict_flag: bool = False


def _latest_indicator(ticker: str, timeframe: str, name: str) -> float | None:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT value FROM technical_indicators
            WHERE ticker = {ph} AND timeframe = {ph} AND indicator_name = {ph}
            ORDER BY date DESC LIMIT 1
            """,
            (ticker, timeframe, name),
        )
        row = cur.fetchone()
    return float(row[0]) if row else None


def _latest_close_gbx(ticker: str) -> float | None:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT close_gbx FROM daily_prices WHERE ticker = {ph} ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        row = cur.fetchone()
    return float(row[0]) if row else None


def confluence_score(ticker: str, daily_close: float | None = None) -> tuple[int, bool]:
    """
    Score 0–3 bullish timeframes; conflict_flag if daily bullish vs weekly/monthly bearish.
    """
    bullish = 0
    daily_bull = False
    weekly_bear = False
    monthly_bear = False

    prices = {
        "daily": daily_close or _latest_close_gbx(ticker),
        "weekly": _latest_close_gbx(ticker),
        "monthly": _latest_close_gbx(ticker),
    }

    for tf in ("daily", "weekly", "monthly"):
        price = prices.get(tf)
        sma50 = _latest_indicator(ticker, tf, "sma_50")
        rsi = _latest_indicator(ticker, tf, "rsi_14")
        if price is None or sma50 is None:
            continue
        is_bull = price > sma50 and (rsi is None or rsi < 65)
        if is_bull:
            bullish += 1
        if tf == "daily" and is_bull:
            daily_bull = True
        if tf == "weekly" and not is_bull and rsi and rsi > 50:
            weekly_bear = True
        if tf == "monthly" and not is_bull:
            monthly_bear = True

    conflict = daily_bull and (weekly_bear or monthly_bear)
    return min(bullish, 3), conflict


def analyst_upside_score(current_gbx: float, snap: AnalystSnapshot | None, cap_pct: float = 30.0) -> float:
    """Score 0–100 from analyst target upside."""
    if not snap or not snap.target_mean or current_gbx <= 0:
        return 0.0
    upside = (snap.target_mean - current_gbx) / current_gbx * 100
    if upside <= 0:
        return 0.0
    return min(100.0, upside / cap_pct * 100)


def catalyst_score(ticker: str, within_weeks: int = 8) -> float:
    """Score 0–100 based on nearest upcoming catalyst (peak at 2–8 weeks)."""
    ph = get_placeholder()
    today = date.today()
    horizon = today + timedelta(weeks=within_weeks)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT event_date FROM catalysts
            WHERE ticker = {ph} AND event_date IS NOT NULL
              AND event_date >= {ph} AND event_date <= {ph}
            ORDER BY event_date ASC LIMIT 1
            """,
            (ticker, today.isoformat(), horizon.isoformat()),
        )
        row = cur.fetchone()
    if not row or not row[0]:
        return 0.0
    try:
        event_date = date.fromisoformat(str(row[0])[:10])
    except ValueError:
        return 0.0
    days = (event_date - today).days
    weeks = days / 7
    if weeks < 1:
        return 60.0
    if 2 <= weeks <= 8:
        return 100.0
    if weeks < 2:
        return 70.0 + weeks * 15
    return max(0.0, 100.0 - (weeks - 8) * 20)


def news_sentiment_score(ticker: str) -> float:
    """Average recent news sentiment scaled to 0–100."""
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT AVG(sentiment_score) FROM news_items
            WHERE ticker = {ph} AND sentiment_score IS NOT NULL
            """,
            (ticker,),
        )
        row = cur.fetchone()
    if not row or row[0] is None:
        return 50.0  # neutral
    # compound -1..1 → 0..100
    return (float(row[0]) + 1) / 2 * 100


def market_regime_score() -> float:
    """100 if FTSE 100 above 50-day MA, else 0. Cached per run."""
    try:
        import yfinance as yf

        df = yf.Ticker("^FTSE").history(period="3mo")
        if df.empty or len(df) < 50:
            return 50.0
        close = df["Close"]
        sma50 = close.rolling(50).mean().iloc[-1]
        return 100.0 if close.iloc[-1] > sma50 else 0.0
    except Exception:
        return 50.0


def score_stock(
    ticker: str,
    daily_df: pd.DataFrame,
    analyst: AnalystSnapshot | None,
    weights: dict | None = None,
) -> StockScore:
    """Calculate composite score for one stock."""
    config = load_config()
    w = weights or config.get("scoring", {})

    levels = analyse_levels(daily_df)
    price = levels.get("price_gbx", 0)
    conf, conflict = confluence_score(ticker, daily_close=price)

    features = {
        "support_score": levels.get("support_score", 0),
        "distance_support_pct": levels.get("distance_support_pct"),
        "distance_resistance_pct": levels.get("distance_resistance_pct"),
        "confluence": conf,
        "conflict_flag": conflict,
        "analyst_upside_score": analyst_upside_score(price, analyst),
        "catalyst_score": catalyst_score(ticker),
        "news_sentiment_score": news_sentiment_score(ticker),
        "market_regime_score": market_regime_score(),
        "sector_relative_score": 50.0,  # Phase 3 placeholder
        "rsi_daily": _latest_indicator(ticker, "daily", "rsi_14"),
        "analyst_target": analyst.target_mean if analyst else None,
        "analyst_count": analyst.analyst_count if analyst else 0,
    }

    composite = (
        w.get("support_proximity", 0.25) * features["support_score"]
        + w.get("multi_tf_confluence", 0.20) * (conf / 3 * 100)
        + w.get("analyst_upside", 0.15) * features["analyst_upside_score"]
        + w.get("catalyst_proximity", 0.15) * features["catalyst_score"]
        + w.get("news_sentiment", 0.10) * features["news_sentiment_score"]
        + w.get("market_regime", 0.10) * features["market_regime_score"]
        + w.get("sector_relative", 0.05) * features["sector_relative_score"]
    )

    return StockScore(
        ticker=ticker,
        composite_score=round(composite, 2),
        features=features,
        conflict_flag=conflict,
    )


def rank_candidates(scores: list[StockScore], top_n: int = 10) -> list[StockScore]:
    """Rank by composite score; deprioritise conflict flags."""
    def sort_key(s: StockScore) -> tuple:
        penalty = -20 if s.conflict_flag else 0
        return (s.composite_score + penalty, s.ticker)

    return sorted(scores, key=sort_key, reverse=True)[:top_n]
