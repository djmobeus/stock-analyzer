"""Tests for catalyst extraction and Yahoo calendars."""

from datetime import date
from unittest.mock import MagicMock, patch

from intelligence.catalysts import (
    calendar_catalysts_from_yfinance,
    detect_event_type,
    extract_catalysts_from_article,
    extract_dates,
    is_upcoming,
)


def test_extract_dates_full_and_abbreviated():
    dates = extract_dates("Results on 15 September 2026 and AGM 3 Oct 2026")
    assert date(2026, 9, 15) in dates
    assert date(2026, 10, 3) in dates


def test_extract_dates_yearless_infers_future(monkeypatch):
    today = date(2026, 7, 21)
    dates = extract_dates("Trading update 12 August", today=today)
    assert date(2026, 8, 12) in dates


def test_detect_event_types():
    assert detect_event_type("Company announces interim results") == "results"
    assert detect_event_type("Q2 trading update") == "trading_update"
    assert detect_event_type("Notice of AGM") == "agm"


def test_extract_catalyst_requires_event():
    cats = extract_catalysts_from_article(
        "TEST.L", "Random headline with no event", "", "test"
    )
    assert cats == []


def test_extract_catalyst_with_date():
    cats = extract_catalysts_from_article(
        "TEST.L",
        "Interim results due 20 August 2026",
        "",
        "test",
    )
    assert len(cats) == 1
    assert cats[0].event_type == "results"
    assert cats[0].event_date == date(2026, 8, 20)


def test_is_upcoming_eight_weeks():
    today = date.today()
    assert is_upcoming(today + __import__("datetime").timedelta(weeks=4))
    assert not is_upcoming(today + __import__("datetime").timedelta(weeks=20))


def test_calendar_from_yfinance_mock():
    fake = MagicMock()
    fake.calendar = {
        "Earnings Date": [date(2026, 11, 12)],
        "Ex-Dividend Date": date(2026, 9, 1),
    }
    fake.get_earnings_dates.return_value = None
    with patch("yfinance.Ticker", return_value=fake):
        cats = calendar_catalysts_from_yfinance("III.L")
    types = {c.event_type for c in cats}
    assert "results" in types
    assert "ex_dividend" in types
