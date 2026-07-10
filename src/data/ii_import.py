"""Interactive Investor CSV holdings import."""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Common II / generic export column aliases
_TICKER_COLS = {"symbol", "ticker", "epic", "stock", "code"}
_NAME_COLS = {"name", "description", "instrument", "security"}
_QTY_COLS = {"quantity", "qty", "units", "shares", "holding"}
_PRICE_COLS = {"price", "avg price", "average price", "cost", "avg cost", "book cost"}

# Yahoo uses BT-A.L for BT Group (Symbol BT.A on II)
_YAHOO_EPIC_ALIASES = {
    "BT.A": "BT-A.L",
}


@dataclass
class HoldingRow:
    ticker: str
    name: str | None
    quantity: float
    avg_cost_gbx: float | None


@dataclass
class _Position:
    quantity: float = 0.0
    cost_pence: float = 0.0
    name: str | None = None


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
    if e in _YAHOO_EPIC_ALIASES:
        return _YAHOO_EPIC_ALIASES[e]
    if e.endswith(".L"):
        return e
    return f"{e}.L"


def _parse_money(value: str | None) -> float | None:
    if not value:
        return None
    text = _clean_cell(str(value))
    if not text or text.lower() in {"n/a", "-", ""}:
        return None
    try:
        return float(text.replace("£", "").replace(",", ""))
    except ValueError:
        return None


def _parse_price_gbx(value: str | None) -> float | None:
    """Parse II price column (£ per share) into pence."""
    pounds = _parse_money(value)
    if pounds is None:
        return None
    return pounds * 100 if pounds < 500 else pounds


def _parse_uk_date(value: str | None) -> datetime:
    if not value:
        return datetime.min
    text = _clean_cell(value)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.min


def _short_name(description: str, symbol: str) -> str:
    """Prefer a short label over the full II description line."""
    desc = _clean_cell(description)
    if not desc:
        return symbol
    m = re.match(r"^\d+\s+(.+?)\s+Del\b", desc, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.match(r"Div\s+\d+\s+(.+?)(?:\s+ORD|\s+GBP|$)", desc, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return desc[:60]


def _is_activity_export(headers: list[str]) -> bool:
    norms = {_norm_header(h) for h in headers}
    return "debit" in norms and "credit" in norms and "symbol" in norms


def _parse_holdings_export(reader: csv.DictReader, clean_headers: list[str]) -> list[HoldingRow]:
    """Classic holdings export: one row per open position."""
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
        raw_ticker = (line.get(ticker_col) or "").strip()
        if not raw_ticker or raw_ticker.lower() in {"symbol", "total", "n/a"}:
            continue
        try:
            qty = float(str(line.get(qty_col, "0")).replace(",", ""))
        except ValueError:
            continue
        if qty <= 0:
            continue

        avg_cost = None
        if price_col and line.get(price_col):
            avg_cost = _parse_price_gbx(str(line[price_col]))

        rows.append(
            HoldingRow(
                ticker=normalise_epic(raw_ticker),
                name=(line.get(name_col) or "").strip() or None if name_col else None,
                quantity=qty,
                avg_cost_gbx=avg_cost,
            )
        )
    return rows


def _parse_activity_export(reader: csv.DictReader, clean_headers: list[str]) -> list[HoldingRow]:
    """
    II account activity / transaction CSV.

    Nets buys (Debit) and sells (Credit) per symbol. Dividend-only rows
    with ``Div NNN`` in the description infer an open position when no
    trades appear in the export window.
    """
    symbol_col = _pick_col(clean_headers, _TICKER_COLS) or "Symbol"
    qty_col = _pick_col(clean_headers, _QTY_COLS) or "Quantity"
    price_col = _pick_col(clean_headers, _PRICE_COLS, prefer=["price"]) or "Price"
    desc_col = _pick_col(clean_headers, _NAME_COLS) or "Description"
    date_col = _pick_col(clean_headers, {"date"}) or "Date"
    debit_col = _pick_col(clean_headers, {"debit"}) or "Debit"
    credit_col = _pick_col(clean_headers, {"credit"}) or "Credit"

    raw_rows = list(reader)
    raw_rows.sort(
        key=lambda r: (
            _parse_uk_date(r.get(date_col)),
            _clean_cell(r.get(desc_col) or ""),
        )
    )

    positions: dict[str, _Position] = {}

    for line in raw_rows:
        symbol = _clean_cell(line.get(symbol_col) or "")
        if not symbol or symbol.lower() in {"n/a", "symbol"}:
            continue

        desc = _clean_cell(line.get(desc_col) or "")
        qty_raw = _clean_cell(line.get(qty_col) or "")

        if not qty_raw or qty_raw.lower() == "n/a":
            div = re.search(r"Div\s+(\d+(?:\.\d+)?)\s+", desc, re.IGNORECASE)
            if div:
                ticker = normalise_epic(symbol)
                qty = float(div.group(1))
                if ticker not in positions and qty > 0:
                    positions[ticker] = _Position(
                        quantity=qty,
                        cost_pence=0.0,
                        name=_short_name(desc, symbol),
                    )
            continue

        try:
            qty = float(qty_raw.replace(",", ""))
        except ValueError:
            continue
        if qty <= 0:
            continue

        ticker = normalise_epic(symbol)
        debit = _parse_money(line.get(debit_col))
        credit = _parse_money(line.get(credit_col))
        price_gbx = _parse_price_gbx(line.get(price_col))

        if debit is not None and credit is None:
            pos = positions.setdefault(ticker, _Position())
            if price_gbx is not None:
                pos.cost_pence += qty * price_gbx
            else:
                pos.cost_pence += debit * 100
            pos.quantity += qty
            pos.name = pos.name or _short_name(desc, symbol)
        elif credit is not None and debit is None:
            pos = positions.get(ticker)
            # II puts some purchases in Credit; if we already hold enough, treat as sell.
            if pos and pos.quantity >= qty:
                sell_qty = min(qty, pos.quantity)
                remaining = pos.quantity - sell_qty
                if pos.quantity > 0:
                    pos.cost_pence *= remaining / pos.quantity
                pos.quantity = remaining
                if pos.quantity <= 0.0001:
                    del positions[ticker]
            else:
                pos = positions.setdefault(ticker, _Position())
                if price_gbx is not None:
                    pos.cost_pence += qty * price_gbx
                else:
                    pos.cost_pence += credit * 100
                pos.quantity += qty
                pos.name = pos.name or _short_name(desc, symbol)
        else:
            logger.debug("%s: skipped ambiguous debit/credit row", ticker)

    rows: list[HoldingRow] = []
    for ticker, pos in sorted(positions.items()):
        if pos.quantity <= 0:
            continue
        avg = pos.cost_pence / pos.quantity if pos.cost_pence > 0 and pos.quantity > 0 else None
        rows.append(
            HoldingRow(
                ticker=ticker,
                name=pos.name,
                quantity=round(pos.quantity, 4),
                avg_cost_gbx=round(avg, 2) if avg is not None else None,
            )
        )

    logger.info("Netted %d open holdings from II activity CSV", len(rows))
    return rows


def parse_ii_csv(content: str | bytes) -> list[HoldingRow]:
    """
    Parse Interactive Investor CSV export.

    Supports:
    - Holdings export (Symbol, Qty, Average Price)
    - Account activity / transaction history (Symbol, Quantity, Debit, Credit)

    Handles UTF-8 with optional / repeated BOMs and flexible column names.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content
    text = text.replace("\ufeff", "")

    lines = text.splitlines()
    if lines:
        lines[0] = lines[0].replace("\ufeff", "")
        text = "\n".join(lines)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    raw_headers = list(reader.fieldnames)
    clean_headers = [_clean_cell(h) for h in raw_headers]
    key_map = {raw: clean for raw, clean in zip(raw_headers, clean_headers)}
    reader.fieldnames = clean_headers

    def _remap(line: dict) -> dict:
        return {key_map.get(k, _clean_cell(k)): v for k, v in line.items()}

    if _is_activity_export(clean_headers):
        remapped = [_remap(r) for r in reader]
        activity_reader = csv.DictReader(io.StringIO(""), fieldnames=clean_headers)
        activity_reader.fieldnames = clean_headers
        rows = _parse_activity_export(iter(remapped), clean_headers)
    else:
        remapped = [_remap(r) for r in reader]
        holdings_reader = csv.DictReader(io.StringIO(""), fieldnames=clean_headers)
        holdings_reader.fieldnames = clean_headers
        rows = _parse_holdings_export(iter(remapped), clean_headers)

    logger.info("Parsed %d holdings from CSV", len(rows))
    return rows
