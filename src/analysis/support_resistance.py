"""Support and resistance level detection."""

from __future__ import annotations

import numpy as np
import pandas as pd


def pivot_points(row: pd.Series) -> dict[str, float]:
    """Standard pivot point from OHLC."""
    h, l, c = float(row["High"]), float(row["Low"]), float(row["Close"])
    pivot = (h + l + c) / 3
    return {
        "pivot": pivot,
        "s1": 2 * pivot - h,
        "s2": pivot - (h - l),
        "r1": 2 * pivot - l,
        "r2": pivot + (h - l),
    }


def fractal_levels(df: pd.DataFrame, lookback: int = 12) -> tuple[list[float], list[float]]:
    """
    Find support/resistance from fractal pivots (local min/max).

    A level must have reversed at least twice in lookback months (daily bars).
    """
    if len(df) < 10:
        return [], []

    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)

    resistance_candidates: list[float] = []
    support_candidates: list[float] = []

    for i in range(2, n - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            resistance_candidates.append(float(highs[i]))
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            support_candidates.append(float(lows[i]))

    # Cluster nearby levels (within 2%)
    def cluster(levels: list[float]) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters: list[list[float]] = [[levels[0]]]
        for lv in levels[1:]:
            if abs(lv - clusters[-1][-1]) / clusters[-1][-1] < 0.02:
                clusters[-1].append(lv)
            else:
                clusters.append([lv])
        # Keep levels touched at least twice
        return [float(np.mean(c)) for c in clusters if len(c) >= 2]

    return cluster(support_candidates), cluster(resistance_candidates)


def nearest_level(price: float, levels: list[float]) -> float | None:
    """Nearest support/resistance level below/above price."""
    if not levels:
        return None
    return min(levels, key=lambda x: abs(x - price))


def distance_pct(price: float, level: float | None) -> float | None:
    """Distance from price to level as % of price."""
    if level is None or price <= 0:
        return None
    return abs(price - level) / price * 100


def support_proximity_score(distance_pct_val: float | None, peak_at: float = 3.0) -> float:
    """
    Score 0–100: higher when closer to support (within peak_at %).
    """
    if distance_pct_val is None:
        return 0.0
    if distance_pct_val <= 0:
        return 100.0
    if distance_pct_val >= peak_at * 2:
        return 0.0
    if distance_pct_val <= peak_at:
        return 100.0 * (1 - distance_pct_val / peak_at)
    # Tail off between peak_at and 2*peak_at
    return max(0.0, 50.0 * (1 - (distance_pct_val - peak_at) / peak_at))


def analyse_levels(df: pd.DataFrame) -> dict:
    """Full support/resistance analysis for a price series."""
    if df.empty:
        return {}
    price = float(df["Close"].iloc[-1])
    supports, resistances = fractal_levels(df.tail(252))  # ~12 months daily

    # Include recent pivot S1 as support candidate
    pivots = pivot_points(df.iloc[-1])
    all_supports = supports + [pivots["s1"], pivots["s2"]]
    all_resistances = resistances + [pivots["r1"], pivots["r2"]]

    # Nearest support below current price
    below = [s for s in all_supports if s <= price * 1.01]
    above = [r for r in all_resistances if r >= price * 0.99]

    nearest_support = max(below) if below else (min(all_supports) if all_supports else None)
    nearest_resistance = min(above) if above else (max(all_resistances) if all_resistances else None)

    dist_support = distance_pct(price, nearest_support)
    dist_resistance = distance_pct(price, nearest_resistance)

    return {
        "price_gbx": price,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "distance_support_pct": dist_support,
        "distance_resistance_pct": dist_resistance,
        "support_score": support_proximity_score(dist_support),
    }
