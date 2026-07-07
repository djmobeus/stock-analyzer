"""Fundamental and analyst data via yfinance (UK/LSE — free)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import yfinance as yf

from config.loader import load_config
from data.universe import StockRecord
from db.connection import get_connection, get_placeholder

logger = logging.getLogger(__name__)

TRUST_REIT_PATTERNS = re.compile(
    r"investment trust|\breit\b|real estate investment|"
    r"\bit plc\b|\bit ltd\b|unit trust",
    re.IGNORECASE,
)

# Yahoo recommendationKey → rough buy/hold/sell weighting
_BUY_KEYS = {"buy", "strong_buy", "strongbuy"}
_SELL_KEYS = {"sell", "strong_sell", "strongsell"}


@dataclass
class AnalystSnapshot:
    ticker: str
    target_mean: float | None
    target_high: float | None
    target_low: float | None
    buy_count: int
    hold_count: int
    sell_count: int
    analyst_count: int
    fcf_improving: bool | None = None
    sector: str | None = None
    name: str | None = None
    industry: str | None = None


def is_trust_or_reit(name: str | None, sector: str | None = None, industry: str | None = None) -> bool:
    """Filter 5: exclude investment trusts and REITs."""
    text = " ".join(filter(None, [name, sector, industry]))
    if TRUST_REIT_PATTERNS.search(text):
        return True
    if sector and "real estate" in sector.lower() and industry and "reit" in industry.lower():
        return True
    return False


def _fcf_positive(info: dict) -> bool | None:
    """Filter 6: positive free cash flow (best effort from yfinance)."""
    fcf = info.get("freeCashflow")
    if fcf is not None:
        return float(fcf) > 0
    op_cf = info.get("operatingCashflow")
    if op_cf is not None:
        return float(op_cf) > 0
    return None


def _parse_recommendation_counts(info: dict, analyst_count: int) -> tuple[int, int, int]:
    """Derive buy/hold/sell from recommendationKey when breakdown unavailable."""
    key = (info.get("recommendationKey") or "").lower().replace(" ", "_")
    if analyst_count <= 0:
        return 0, 0, 0
    if key in _BUY_KEYS:
        return analyst_count, 0, 0
    if key in _SELL_KEYS:
        return 0, 0, analyst_count
    if key == "hold":
        return 0, analyst_count, 0
    # Unknown — assume neutral split
    return 0, analyst_count, 0


def fetch_analyst_snapshot(ticker: str) -> AnalystSnapshot | None:
    """Fetch analyst consensus and fundamentals from yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as exc:
        logger.warning("%s: yfinance info failed: %s", ticker, exc)
        return None

    if not info:
        return None

    analyst_count = int(info.get("numberOfAnalystOpinions") or 0)
    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")

    # No analyst coverage at all
    if analyst_count == 0 and not target_mean:
        return None

    buy, hold, sell = _parse_recommendation_counts(info, analyst_count)

    return AnalystSnapshot(
        ticker=ticker,
        target_mean=float(target_mean) if target_mean else None,
        target_high=float(target_high) if target_high else None,
        target_low=float(target_low) if target_low else None,
        buy_count=buy,
        hold_count=hold,
        sell_count=sell,
        analyst_count=analyst_count,
        fcf_improving=_fcf_positive(info),
        sector=info.get("sector"),
        name=info.get("shortName") or info.get("longName"),
        industry=info.get("industry"),
    )


def analyst_data_is_fresh(ticker: str, max_age_days: int = 7) -> bool:
    """True if analyst_data was updated within max_age_days."""
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT last_updated FROM analyst_data WHERE ticker = {ph}",
            (ticker,),
        )
        row = cur.fetchone()
    if not row or not row[0]:
        return False
    try:
        updated = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - updated < timedelta(days=max_age_days)
    except ValueError:
        return False


def apply_fundamental_filters(
    snapshot: AnalystSnapshot,
    min_analysts: int = 4,
) -> tuple[bool, str | None]:
    """Filters 4–6. Returns (passed, reject_reason)."""
    if is_trust_or_reit(snapshot.name, snapshot.sector, snapshot.industry):
        return False, "trust_or_reit"

    if snapshot.analyst_count < min_analysts:
        return False, f"analyst_count_{snapshot.analyst_count}"

    if snapshot.fcf_improving is False:
        return False, "negative_fcf"

    return True, None


def upsert_analyst_snapshot(snap: AnalystSnapshot) -> None:
    """Save analyst data to database."""
    ph = get_placeholder()
    now = datetime.now(timezone.utc).isoformat()
    sql = f"""
        INSERT INTO analyst_data
            (ticker, target_mean, target_high, target_low,
             buy_count, hold_count, sell_count, analyst_count, last_updated)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ON CONFLICT (ticker) DO UPDATE SET
            target_mean = excluded.target_mean,
            target_high = excluded.target_high,
            target_low = excluded.target_low,
            buy_count = excluded.buy_count,
            hold_count = excluded.hold_count,
            sell_count = excluded.sell_count,
            analyst_count = excluded.analyst_count,
            last_updated = excluded.last_updated
    """
    with get_connection() as conn:
        conn.cursor().execute(
            sql,
            (
                snap.ticker,
                snap.target_mean,
                snap.target_high,
                snap.target_low,
                snap.buy_count,
                snap.hold_count,
                snap.sell_count,
                snap.analyst_count,
                now,
            ),
        )


def snapshot_from_db(ticker: str) -> AnalystSnapshot | None:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT target_mean, target_high, target_low,
                   buy_count, hold_count, sell_count, analyst_count
            FROM analyst_data WHERE ticker = {ph}
            """,
            (ticker,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return AnalystSnapshot(
        ticker=ticker,
        target_mean=row[0],
        target_high=row[1],
        target_low=row[2],
        buy_count=row[3] or 0,
        hold_count=row[4] or 0,
        sell_count=row[5] or 0,
        analyst_count=row[6] or 0,
    )


def enrich_and_filter_universe(
    records: list[StockRecord],
    min_analysts: int = 4,
    cache_days: int = 7,
) -> list[StockRecord]:
    """Apply filters 4–6 using yfinance; returns stocks that pass."""
    passed: list[StockRecord] = []
    for i, rec in enumerate(records, 1):
        logger.info("Fundamentals %d/%d: %s", i, len(records), rec.ticker)

        if analyst_data_is_fresh(rec.ticker, cache_days):
            snap = snapshot_from_db(rec.ticker)
            if snap and apply_fundamental_filters(snap, min_analysts)[0]:
                if snap.name:
                    rec.name = snap.name
                if snap.sector:
                    rec.sector = snap.sector
                passed.append(rec)
            continue

        snap = fetch_analyst_snapshot(rec.ticker)
        if not snap:
            logger.debug("%s: no yfinance analyst data — skipping", rec.ticker)
            continue

        upsert_analyst_snapshot(snap)
        ok, reason = apply_fundamental_filters(snap, min_analysts)
        if ok:
            if snap.name:
                rec.name = snap.name
            if snap.sector:
                rec.sector = snap.sector
            passed.append(rec)
        else:
            logger.debug("%s: fundamental filter failed: %s", rec.ticker, reason)

    logger.info("Fundamental filter: %d -> %d stocks", len(records), len(passed))
    return passed
