"""Catalyst date extraction from RNS, news text, and Yahoo calendars."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Event type patterns (UK-friendly)
EVENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "results",
        re.compile(
            r"full.?year|half.?year|interim results|preliminary|"
            r"annual results|final results|FY\s?\d{2}|H[12]\s+results|"
            r"Q[1-4]\s+results|earnings|results for the",
            re.I,
        ),
    ),
    ("trading_update", re.compile(r"trading update|Q[1-4] update|pre.?close", re.I)),
    ("agm", re.compile(r"\bAGM\b|annual general meeting|capital markets day|\bCMD\b", re.I)),
    ("ex_dividend", re.compile(r"ex.?dividend|dividend declaration|final dividend|interim dividend", re.I)),
]

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_MONTH_ALT = "|".join(MONTHS.keys())

DATE_PATTERNS = [
    # 7 July 2026 / 7th July 2026 / 7 Jul 2026
    re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ALT})\s+(\d{{4}})\b",
        re.I,
    ),
    # 7 July / 7th September (year inferred)
    re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ALT})\b(?!\s+\d{{4}})",
        re.I,
    ),
    # July 2026
    re.compile(rf"\b({_MONTH_ALT})\s+(\d{{4}})\b", re.I),
    # 2026-07-07
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    # 07/07/2026 or 7/7/2026 (UK day/month/year)
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
]


@dataclass
class Catalyst:
    ticker: str
    event_type: str
    event_date: date | None
    description: str
    source: str


def detect_event_type(text: str) -> str | None:
    for event_type, pattern in EVENT_PATTERNS:
        if pattern.search(text):
            return event_type
    return None


def _infer_year(month: int, day: int, today: date | None = None) -> int:
    """Pick current or next year so the date is not far in the past."""
    today = today or date.today()
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return today.year
    if candidate < today - timedelta(days=14):
        return today.year + 1
    return today.year


def extract_dates(text: str, today: date | None = None) -> list[date]:
    """Extract dates from free text (UK formats + year inference)."""
    today = today or date.today()
    found: list[date] = []

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                g = match.groups()
                raw = match.group(0)
                if re.search(r"\d{4}-\d{2}-\d{2}", raw):
                    year, month, day = int(g[0]), int(g[1]), int(g[2])
                    found.append(date(year, month, day))
                elif "/" in raw and len(g) == 3 and g[2].isdigit() and len(g[2]) == 4:
                    day, month, year = int(g[0]), int(g[1]), int(g[2])
                    found.append(date(year, month, day))
                elif len(g) == 3 and g[1].lower() in MONTHS and g[2].isdigit():
                    day = int(g[0])
                    month = MONTHS[g[1].lower()]
                    year = int(g[2])
                    found.append(date(year, month, day))
                elif len(g) == 2 and g[0].lower() in MONTHS and g[1].isdigit():
                    # July 2026 → mid-month placeholder
                    month = MONTHS[g[0].lower()]
                    year = int(g[1])
                    found.append(date(year, month, 15))
                elif len(g) == 2 and g[1].lower() in MONTHS:
                    day = int(g[0])
                    month = MONTHS[g[1].lower()]
                    year = _infer_year(month, day, today)
                    found.append(date(year, month, day))
            except (ValueError, KeyError, IndexError, AttributeError):
                continue

    # Prefer specific day+month+year over "Month YYYY" mid-month placeholders
    uniq = sorted(set(found))
    by_ym: dict[tuple[int, int], list[date]] = {}
    for d in uniq:
        by_ym.setdefault((d.year, d.month), []).append(d)
    out: list[date] = []
    for dates_ym in by_ym.values():
        non_mid = [d for d in dates_ym if d.day != 15]
        out.extend(non_mid if non_mid and len(dates_ym) > 1 else dates_ym)
    return sorted(set(out))


def extract_catalysts_from_article(
    ticker: str,
    title: str,
    summary: str,
    source: str,
) -> list[Catalyst]:
    """Extract catalyst events from a news article."""
    text = f"{title} {summary}"
    event_type = detect_event_type(text)
    if not event_type:
        return []

    dates = extract_dates(text)
    today = date.today()
    # Prefer upcoming dates; fall back to first parsed date
    upcoming = [d for d in dates if d >= today - timedelta(days=7)]
    event_date = (upcoming[0] if upcoming else dates[0]) if dates else None

    # Skip clearly historical events (more than ~2 weeks ago)
    if event_date is not None and event_date < today - timedelta(days=14):
        return []

    return [
        Catalyst(
            ticker=ticker,
            event_type=event_type,
            event_date=event_date,
            description=title[:500],
            source=source,
        )
    ]


def calendar_catalysts_from_yfinance(ticker: str) -> list[Catalyst]:
    """
    Pull earnings / ex-div style dates from Yahoo (much more reliable than RSS alone).
    """
    out: list[Catalyst] = []
    today = date.today()
    horizon = today + timedelta(weeks=26)

    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        cal = t.calendar or {}
        if isinstance(cal, dict):
            earn = cal.get("Earnings Date")
            if isinstance(earn, list):
                for d in earn:
                    if isinstance(d, date) and today <= d <= horizon:
                        out.append(
                            Catalyst(
                                ticker=ticker,
                                event_type="results",
                                event_date=d,
                                description=f"Yahoo earnings date {d.isoformat()}",
                                source="yfinance_calendar",
                            )
                        )
            elif isinstance(earn, date) and today <= earn <= horizon:
                out.append(
                    Catalyst(
                        ticker=ticker,
                        event_type="results",
                        event_date=earn,
                        description=f"Yahoo earnings date {earn.isoformat()}",
                        source="yfinance_calendar",
                    )
                )
            exdiv = cal.get("Ex-Dividend Date")
            if isinstance(exdiv, date) and today <= exdiv <= horizon:
                out.append(
                    Catalyst(
                        ticker=ticker,
                        event_type="ex_dividend",
                        event_date=exdiv,
                        description=f"Yahoo ex-dividend {exdiv.isoformat()}",
                        source="yfinance_calendar",
                    )
                )

        try:
            edf = t.get_earnings_dates(limit=8)
        except Exception:
            edf = None
        if edf is not None and not getattr(edf, "empty", True):
            for ts in edf.index:
                try:
                    d = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
                except Exception:
                    continue
                if today <= d <= horizon:
                    out.append(
                        Catalyst(
                            ticker=ticker,
                            event_type="results",
                            event_date=d,
                            description=f"Yahoo earnings schedule {d.isoformat()}",
                            source="yfinance_earnings",
                        )
                    )
    except Exception as exc:
        logger.debug("yfinance calendar failed for %s: %s", ticker, exc)

    # Dedupe by (event_type, event_date)
    seen: set[tuple] = set()
    unique: list[Catalyst] = []
    for c in out:
        key = (c.event_type, c.event_date)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


def is_upcoming(event_date: date | None, within_weeks: int = 8) -> bool:
    """True if catalyst is dated within the next N weeks (default = hold window)."""
    if event_date is None:
        return False
    today = date.today()
    return today <= event_date <= today + timedelta(weeks=within_weeks)
