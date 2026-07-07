"""Tests for catalyst extraction and sentiment."""

from datetime import date, timedelta

from data.news import is_noise
from intelligence.catalysts import (
    detect_event_type,
    extract_catalysts_from_article,
    extract_dates,
    is_upcoming,
)
from intelligence.sentiment import score_headline


def test_noise_filter():
    assert is_noise("Transaction in Own Shares")
    assert not is_noise("Half Year Results announcement")


def test_detect_results_event():
    assert detect_event_type("Company announces Half Year Results") == "results"


def test_extract_date_from_text():
    dates = extract_dates("Results on 15 July 2026")
    assert len(dates) == 1
    assert dates[0] == date(2026, 7, 15)


def test_extract_catalyst_from_article():
    cats = extract_catalysts_from_article(
        "VOD.L",
        "Vodafone Half Year Results on 12 November 2026",
        "",
        "test",
    )
    assert len(cats) == 1
    assert cats[0].event_type == "results"
    assert cats[0].event_date == date(2026, 11, 12)


def test_upcoming_catalyst():
    soon = date.today() + timedelta(weeks=3)
    assert is_upcoming(soon, within_weeks=6) is True
    far = date.today() + timedelta(weeks=10)
    assert is_upcoming(far, within_weeks=6) is False


def test_sentiment_positive():
    score = score_headline("Company beats earnings expectations with strong growth")
    assert score > 0


def test_sentiment_negative():
    score = score_headline("Profit warning issued amid heavy losses and downgrade")
    assert score < 0
