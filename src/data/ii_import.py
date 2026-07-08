"""Interactive Investor CSV holdings import."""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Common II / generic export column aliases
_TICKER_COLS = {"symbol", "ticker", "epic", "stock", "code"}
_NAME_COLS = {"name", "description", "instrument", "security"}
_QTY_COLS = {"quantity", "qty", "units", "shares", "holding"}
_PRICE_COLS = {"price", "avg price", "average price", "cost", "avg cost", "book cost"}
_VALUE_COLS = {"value", "market value", "current value"}


@dataclass
class HoldingRow:
    ticker: str
    name: str | None
    quantity: float
    avg_cost_gbx: float | None


def _strip_bom(text: str) -> str:
    """Remove UTF-8 BOM characters (Excel/II exports often repeat them)."""
    return text.replace("\ufeff", "")


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", _strip_bom(h).strip().lower())


def _pick_col(headers: list[str], candidates: set[str], prefer: list[str] | None = None) -> str | None:
    """Match column by normalised name; optional preference order."""
    for pref in prefer or []:
        for h in headers:
            if _norm_header(h) == pref:
                return h
    for h in headers:
        norm = _norm_header(h)
        if norm in candidates:
            return h
        for c in candidates:
            if norm.endswith(c):
                return h
    return None


def normalise_epic(epic: str) -> str:
    """Convert II epic to Yahoo LSE ticker."""
    e = epic.strip().upper()
    if not e:
        return e
    if e.endswith(".L"):
        return e
    # II often uses epic without suffix e.g. "AAF" or "PRU"
    return f"{e}.L"


def parse_ii_csv(content: str | bytes) -> list[HoldingRow]:
    """
    Parse Interactive Investor (or similar) CSV export.

    Handles UTF-8 with optional BOM and flexible column names.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content
    text = _strip_bom(text)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    headers = [_strip_bom(h) for h in reader.fieldnames]
    # Re-key rows with clean headers
    reader.fieldnames = headers

    ticker_col = _pick_col(headers, _TICKER_COLS)
    qty_col = _pick_col(headers, _QTY_COLS)
    if not ticker_col or not qty_col:
        raise ValueError(
            f"Could not find ticker/quantity columns. Headers: {headers}"
        )

    name_col = _pick_col(headers, _NAME_COLS)
    price_col = _pick_col(
        headers,
        _PRICE_COLS,
        prefer=["average price", "book cost", "avg price", "price"],
    )

    rows: list[HoldingRow] = []
    for line in reader:
        raw_ticker = (line.get(ticker_col) or "").strip()
        if not raw_ticker or raw_ticker.lower() in {"symbol", "total"}:
            continue
        try:
            qty = float(str(line.get(qty_col, "0")).replace(",", ""))
        except ValueError:
            continue
        if qty <= 0:
            continue

        avg_cost = None
        if price_col and line.get(price_col):
            try:
                # II may show pounds; store as GBX if value < 500 typically pounds
                val = float(str(line[price_col]).replace(",", "").replace("£", "").replace("p", ""))
                avg_cost = val * 100 if val < 500 else val
            except ValueError:
                pass

        rows.append(
            HoldingRow(
                ticker=normalise_epic(raw_ticker),
                name=(line.get(name_col) or "").strip() or None,
                quantity=qty,
                avg_cost_gbx=avg_cost,
            )
        )

    logger.info("Parsed %d holdings from CSV", len(rows))
    return rows
