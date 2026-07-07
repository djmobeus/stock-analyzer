"""Finnhub API client for UK LSE stocks."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from config.loader import get_finnhub_api_key

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
# Stay under 60 calls/min on free tier
_MIN_REQUEST_INTERVAL = 1.05
_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_at = time.monotonic()


def _get(path: str, params: dict | None = None) -> Any | None:
    api_key = get_finnhub_api_key()
    if not api_key:
        return None
    _throttle()
    params = dict(params or {})
    params["token"] = api_key
    try:
        resp = requests.get(f"{FINNHUB_BASE}{path}", params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("Finnhub %s failed: %s", path, exc)
        return None


def fetch_quote(ticker: str) -> dict | None:
    """Latest quote; LSE prices in pence."""
    data = _get("/quote", {"symbol": ticker})
    if not data or data.get("c") in (None, 0):
        return None
    return data


def quote_close_gbx(ticker: str) -> float | None:
    quote = fetch_quote(ticker)
    return float(quote["c"]) if quote else None


# Backwards compatibility
finnhub_close_gbx = quote_close_gbx


def fetch_recommendations(ticker: str) -> list[dict]:
    """Monthly analyst recommendation trends."""
    data = _get("/stock/recommendation", {"symbol": ticker})
    return data if isinstance(data, list) else []


def fetch_price_target(ticker: str) -> dict | None:
    """Consensus price target."""
    data = _get("/stock/price-target", {"symbol": ticker})
    return data if isinstance(data, dict) and data else None


def fetch_profile(ticker: str) -> dict | None:
    """Company profile (sector, industry, name)."""
    data = _get("/stock/profile2", {"symbol": ticker})
    return data if isinstance(data, dict) and data else None


def fetch_basic_financials(ticker: str) -> dict | None:
    """Key financial metrics including free cash flow series."""
    data = _get("/stock/metric", {"symbol": ticker, "metric": "all"})
    return data if isinstance(data, dict) and data else None
