"""External research links for LSE tickers."""

from __future__ import annotations

import json
from pathlib import Path

from config.loader import ROOT_DIR

_SLUGS_PATH = ROOT_DIR / "data" / "investing_slugs.json"
_slugs_cache: dict[str, str] | None = None


def _load_slugs() -> dict[str, str]:
    global _slugs_cache
    if _slugs_cache is not None:
        return _slugs_cache
    if _SLUGS_PATH.exists():
        _slugs_cache = json.loads(_SLUGS_PATH.read_text(encoding="utf-8"))
    else:
        _slugs_cache = {}
    return _slugs_cache


def yahoo_ticker(ticker: str) -> str:
    """Canonical Yahoo symbol."""
    t = ticker.strip().upper()
    if t.endswith(".L"):
        return t
    return f"{t}.L"


def display_epic(ticker: str) -> str:
    """Human LSE-style epic without .L."""
    t = yahoo_ticker(ticker)
    return t[:-2] if t.endswith(".L") else t


def yahoo_finance_url(ticker: str) -> str:
    return f"https://uk.finance.yahoo.com/quote/{yahoo_ticker(ticker)}"


def investing_url(ticker: str) -> str | None:
    """Direct equities URL if slug mapped; else None."""
    yt = yahoo_ticker(ticker)
    epic = display_epic(yt)
    slugs = _load_slugs()
    slug = slugs.get(yt) or slugs.get(epic) or slugs.get(epic.replace(".", "-"))
    if not slug:
        return None
    return f"https://www.investing.com/equities/{slug}"


def research_links(ticker: str) -> dict:
    """Preferred links for UI/email."""
    inv = investing_url(ticker)
    return {
        "yahoo": yahoo_finance_url(ticker),
        "investing": inv,
        "primary": inv or yahoo_finance_url(ticker),
        "primary_label": "Investing.com" if inv else "Yahoo Finance",
    }
