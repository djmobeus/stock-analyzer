"""Catalyst date extraction from RNS and news text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# Event type patterns
EVENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("results", re.compile(r"full.?year|half.?year|interim|preliminary|annual results|trading update", re.I)),
    ("agm", re.compile(r"\bAGM\b|annual general meeting", re.I)),
    ("ex_dividend", re.compile(r"ex.?dividend|dividend declaration", re.I)),
    ("trading_update", re.compile(r"trading update|Q1 update|Q3 update", re.I)),
]

# Date patterns: 7 July 2026, 07/07/2026, 2026-07-07
DATE_PATTERNS = [
    re.compile(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})\b",
        re.I,
    ),
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


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


def extract_dates(text: str) -> list[date]:
    """Extract dates from text."""
    found: list[date] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                if pattern.pattern.startswith(r"\b(\d{1,2})\s+(January"):
                    day, month_name, year = match.groups()
                    month = MONTHS[month_name.lower()]
                    found.append(date(int(year), month, int(day)))
                elif "-" in match.group(0):
                    year, month, day = match.groups()
                    found.append(date(int(year), int(month), int(day)))
                else:
                    day, month, year = match.groups()
                    found.append(date(int(year), int(month), int(day)))
            except (ValueError, KeyError):
                continue
    return found


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
    event_date = dates[0] if dates else None

    return [
        Catalyst(
            ticker=ticker,
            event_type=event_type,
            event_date=event_date,
            description=title[:500],
            source=source,
        )
    ]


def is_upcoming(event_date: date | None, within_weeks: int = 6) -> bool:
    """True if catalyst is dated within the next N weeks."""
    if event_date is None:
        return False
    today = date.today()
    return today <= event_date <= today + timedelta(weeks=within_weeks)
