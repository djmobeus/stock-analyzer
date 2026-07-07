"""Snapshot technical context when logging an observation."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from db.connection import get_connection, get_placeholder
from intelligence.patterns import parse_chart_patterns, pattern_key


def _latest_indicators(ticker: str) -> dict[str, dict[str, float]]:
    """Latest indicator values per timeframe."""
    ph = get_placeholder()
    sql = f"""
        SELECT timeframe, indicator_name, value
        FROM technical_indicators
        WHERE ticker = {ph}
          AND date = (
              SELECT MAX(date) FROM technical_indicators
              WHERE ticker = {ph} AND timeframe = technical_indicators.timeframe
          )
    """
    result: dict[str, dict[str, float]] = {}
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (ticker, ticker))
        for row in cur.fetchall():
            tf, name, value = row[0], row[1], row[2]
            if value is None:
                continue
            result.setdefault(tf, {})[name] = float(value)
    return result


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


def _analyst_snapshot(ticker: str) -> dict:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT target_mean, analyst_count, buy_count, hold_count, sell_count
            FROM analyst_data WHERE ticker = {ph}
            """,
            (ticker,),
        )
        row = cur.fetchone()
    if not row:
        return {}
    return {
        "target_mean": row[0],
        "analyst_count": row[1],
        "buy_count": row[2],
        "hold_count": row[3],
        "sell_count": row[4],
    }


def build_features_snapshot(ticker: str, chart_description: str | None) -> dict:
    """Collect indicator and pattern context at observation time."""
    patterns = parse_chart_patterns(chart_description)
    return {
        "ticker": ticker,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "entry_close_gbx": _latest_close_gbx(ticker),
        "indicators": _latest_indicators(ticker),
        "analyst": _analyst_snapshot(ticker),
        "pattern_types": patterns,
        "pattern_key": pattern_key(patterns),
    }


def features_to_json(features: dict) -> str:
    return json.dumps(features)
