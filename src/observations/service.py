"""Observation logging service."""

from __future__ import annotations

from datetime import datetime, timezone

from db.repositories import get_latest_price_gbx, insert_observation
from observations.context import build_features_snapshot, features_to_json


def normalise_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    if not t.endswith(".L"):
        t = f"{t}.L"
    return t


def log_observation(
    ticker: str,
    prediction: str,
    confidence: str,
    chart_description: str = "",
    entry_price_gbx: float | None = None,
) -> int:
    """
    Log a user observation with full feature snapshot.

    prediction: buy | watch | avoid
    confidence: low | medium | high
    """
    ticker = normalise_ticker(ticker)
    if prediction not in {"buy", "watch", "avoid"}:
        raise ValueError(f"Invalid prediction: {prediction}")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError(f"Invalid confidence: {confidence}")

    features = build_features_snapshot(ticker, chart_description)
    if entry_price_gbx is None:
        entry_price_gbx = features.get("entry_close_gbx") or get_latest_price_gbx(ticker)

    return insert_observation(
        ticker=ticker,
        observed_at=datetime.now(timezone.utc),
        entry_price_gbx=entry_price_gbx,
        prediction=prediction,
        confidence=confidence,
        chart_description=chart_description.strip(),
        features_json=features_to_json(features),
    )
