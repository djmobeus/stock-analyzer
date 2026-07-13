"""Tests for UK pipeline schedule (05:00 Mon–Fri)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pipeline.calendar import (
    is_run_time_window,
    next_briefing_day,
    should_run_pipeline,
    skip_reason,
)

UK = ZoneInfo("Europe/London")


def _uk(year, month, day, hour=5, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=UK)


def test_run_monday_morning():
    assert should_run_pipeline(_uk(2026, 7, 6)) is True  # Monday
    assert next_briefing_day(_uk(2026, 7, 6)) == "Monday"


def test_run_friday_morning():
    assert should_run_pipeline(_uk(2026, 7, 10)) is True  # Friday
    assert next_briefing_day(_uk(2026, 7, 10)) == "Friday"


def test_skip_saturday_and_sunday():
    assert should_run_pipeline(_uk(2026, 7, 11)) is False  # Saturday
    assert should_run_pipeline(_uk(2026, 7, 12)) is False  # Sunday
    assert "Saturday" in skip_reason(_uk(2026, 7, 11))


def test_run_time_window_at_5am():
    assert is_run_time_window(_uk(2026, 7, 6, 5, 10)) is True
    assert is_run_time_window(_uk(2026, 7, 6, 12, 0)) is False


def test_morning_delivery_window_until_7am():
    from pipeline.calendar import is_morning_delivery_window

    assert is_morning_delivery_window(_uk(2026, 7, 6, 5, 0)) is True
    assert is_morning_delivery_window(_uk(2026, 7, 6, 6, 45)) is True
    assert is_morning_delivery_window(_uk(2026, 7, 6, 7, 0)) is True
    assert is_morning_delivery_window(_uk(2026, 7, 6, 7, 30)) is False
