"""FTSE 100/250 universe builder and filters."""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from config.loader import ROOT_DIR, load_config

logger = logging.getLogger(__name__)

EXCLUSIONS_PATH = ROOT_DIR / "data" / "exclusions.csv"
WIKI_FTSE100 = "https://en.wikipedia.org/wiki/FTSE_100_Index"
WIKI_FTSE250 = "https://en.wikipedia.org/wiki/FTSE_250_Index"


@dataclass
class StockRecord:
    ticker: str
    name: str | None = None
    sector: str | None = None
    market_cap_gbp: float | None = None
    avg_volume: float | None = None


def load_exclusions() -> set[str]:
    """Load tickers to exclude (dual-listed, etc.)."""
    excluded: set[str] = set()
    if not EXCLUSIONS_PATH.exists():
        return excluded
    with EXCLUSIONS_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "").strip().upper()
            if ticker:
                excluded.add(ticker)
    return excluded


def _normalise_epic(epic: str) -> str | None:
    """Convert Wikipedia EPIC to yfinance ticker (e.g. SHEL -> SHEL.L)."""
    if not epic or not isinstance(epic, str):
        return None
    epic = epic.strip().upper()
    epic = re.sub(r"\[.*?\]", "", epic).strip()  # remove footnotes
    if not epic or epic in ("EPIC", "TICKER"):
        return None
    if epic.endswith(".L"):
        return epic
    return f"{epic}.L"


def _fetch_wikipedia_constituents(url: str, index_name: str) -> list[str]:
    """Scrape constituent EPICs from a Wikipedia index page."""
    headers = {"User-Agent": "UKStockAnalyzer/0.1 (educational project)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    tickers: list[str] = []
    for table in tables:
        cols = {str(c).lower(): c for c in table.columns}
        epic_col = None
        for key in ("epic", "ticker", "symbol"):
            if key in cols:
                epic_col = cols[key]
                break
        if epic_col is None:
            continue
        for val in table[epic_col].dropna():
            t = _normalise_epic(str(val))
            if t:
                tickers.append(t)
    if not tickers:
        raise ValueError(f"No tickers found on Wikipedia page for {index_name}")
    return sorted(set(tickers))


def fetch_ftse_constituents() -> list[str]:
    """Return combined unique FTSE 100 + FTSE 250 tickers as .L symbols."""
    ftse100 = _fetch_wikipedia_constituents(WIKI_FTSE100, "FTSE 100")
    ftse250 = _fetch_wikipedia_constituents(WIKI_FTSE250, "FTSE 250")
    combined = sorted(set(ftse100 + ftse250))
    logger.info("Fetched %d FTSE 100 + %d FTSE 250 -> %d unique", len(ftse100), len(ftse250), len(combined))
    return combined


def apply_listing_filter(tickers: list[str], exclusions: set[str]) -> list[str]:
    """Filter 1: LSE .L only, remove exclusions."""
    result = []
    for t in tickers:
        if not t.endswith(".L"):
            continue
        if t.upper() in exclusions:
            continue
        result.append(t)
    return result


def fetch_stock_metrics(ticker: str) -> StockRecord:
    """Fetch market cap and volume from yfinance info."""
    t = yf.Ticker(ticker)
    info: dict = {}
    try:
        info = t.info or {}
    except Exception:
        pass

    market_cap = info.get("marketCap")
    avg_vol = info.get("averageVolume") or info.get("averageVolume10days")

    # Fallback: calculate 20-day average volume from recent history
    if not avg_vol:
        try:
            hist = t.history(period="1mo")
            if not hist.empty and "Volume" in hist.columns:
                avg_vol = float(hist["Volume"].tail(20).mean())
        except Exception:
            pass

    name = info.get("shortName") or info.get("longName")
    sector = info.get("sector")

    return StockRecord(
        ticker=ticker,
        name=name,
        sector=sector,
        market_cap_gbp=float(market_cap) if market_cap else None,
        avg_volume=float(avg_vol) if avg_vol else None,
    )


def apply_volume_and_cap_filters(
    records: list[StockRecord],
    min_volume: float,
    min_market_cap: float,
) -> list[StockRecord]:
    """Filters 2 and 3: minimum volume and market cap."""
    passed: list[StockRecord] = []
    for rec in records:
        if rec.avg_volume is not None and rec.avg_volume < min_volume:
            continue
        if rec.market_cap_gbp is not None and rec.market_cap_gbp < min_market_cap:
            continue
        # If metrics missing, keep ticker but log — price history may still work
        if rec.avg_volume is None and rec.market_cap_gbp is None:
            logger.warning("%s: missing volume and market cap — keeping for now", rec.ticker)
        passed.append(rec)
    return passed


def build_filtered_universe(metrics_limit: int | None = None) -> list[StockRecord]:
    """
    Build the filtered tradeable universe.

    Returns list of StockRecord passing filters 1–3.
    metrics_limit: if set, only fetch metrics for first N tickers (testing).
    """
    config = load_config()
    universe_cfg = config.get("universe", {})
    min_vol = universe_cfg.get("min_avg_volume", 500_000)
    min_cap = universe_cfg.get("min_market_cap_gbp", 300_000_000)

    exclusions = load_exclusions()
    raw = fetch_ftse_constituents()
    listed = apply_listing_filter(raw, exclusions)
    if metrics_limit:
        listed = listed[:metrics_limit]

    records: list[StockRecord] = []
    for i, ticker in enumerate(listed, 1):
        logger.info("Metrics %d/%d: %s", i, len(listed), ticker)
        try:
            records.append(fetch_stock_metrics(ticker))
        except Exception as exc:
            logger.warning("Failed metrics for %s: %s", ticker, exc)
            records.append(StockRecord(ticker=ticker))

    filtered = apply_volume_and_cap_filters(records, min_vol, min_cap)
    logger.info("Universe: %d raw -> %d after filters", len(listed), len(filtered))
    return filtered


def universe_as_of() -> datetime:
    return datetime.now(timezone.utc)
