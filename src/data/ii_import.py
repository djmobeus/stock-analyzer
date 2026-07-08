"""Interactive Investor CSV holdings import."""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Common II / generic export column aliases
_TICKER_COLS = {"symbol", "ticker", "epic", "stock", "code"}
_NAME_COLS = {"name", "description", "instrument", "security"}
_QTY_COLS = {"quantity", "qty", "units", "shares", "holding"}
_PRICE_COLS = {"price", "avg price", "average price", "cost", "avg cost", "book cost"}


@dataclass
class HoldingRow:
    ticker: str
    name: str | None
    quantity: float
    avg_cost_gbx: float | None


def _clean_cell(text: str) -> str:
    """Strip BOM, zero-width chars, and whitespace."""
    text = text.replace("\ufeff", "")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
    return text.strip()


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", _clean_cell(h).lower())


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
            if norm.endswith(c) or norm.startswith(c):
                return h
    return None


def normalise_epic(epic: str) -> str:
    """Convert II epic to Yahoo LSE ticker."""
    e = _clean_cell(epic).upper()
    if not e:
        return e
    if e.endswith(".L"):
        return e
    return f"{e}.L"


def parse_ii_csv(content: str | bytes) -> list[HoldingRow]:
    """
    Parse Interactive Investor (or similar) CSV export.

    Handles UTF-8 with optional / repeated BOMs and flexible column names.
    """
    if isinstance(content, bytes):
        # utf-8-sig strips one leading BOM; replace removes any remaining
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content
    text = text.replace("\ufeff", "")

    # Clean header line proactively before DictReader sees it
    lines = text.splitlines()
    if lines:
        lines[0] = lines[0].replace("\ufeff", "")
        text = "\n".join(lines)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    raw_headers = list(reader.fieldnames)
    clean_headers = [_clean_cell(h) for h in raw_headers]
    # Map original key → cleaned key for row lookups
    key_map = {raw: clean for raw, clean in zip(raw_headers, clean_headers)}
    reader.fieldnames = clean_headers

    ticker_col = _pick_col(clean_headers, _TICKER_COLS)
    qty_col = _pick_col(clean_headers, _QTY_COLS)
    if not ticker_col or not qty_col:
        raise ValueError(
            f"Could not find ticker/quantity columns. Headers: {clean_headers}"
        )

    name_col = _pick_col(clean_headers, _NAME_COLS)
    price_col = _pick_col(
        clean_headers,
        _PRICE_COLS,
        prefer=["average price", "book cost", "avg price", "price"],
    )

    rows: list[HoldingRow] = []
    for line in reader:
        # Defensive: also try remapping if DictReader ignored fieldnames reset
        if ticker_col not in line and key_map:
            line = {key_map.get(k, _clean_cell(k)): v for k, v in line.items()}

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
                val = float(
                    str(line[price_col]).replace(",", "").replace("£", "").replace("p", "")
                )
                avg_cost = val * 100 if val < 500 else val
            except ValueError:
                pass

        rows.append(
            HoldingRow(
                ticker=normalise_epic(raw_ticker),
                name=(line.get(name_col) or "").strip() or None if name_col else None,
                quantity=qty,
                avg_cost_gbx=avg_cost,
            )
        )

    logger.info("Parsed %d holdings from CSV", len(rows))
    return rows
