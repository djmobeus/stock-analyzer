"""
UK market schedule for the morning pipeline.

Runs at 05:00 UK on trading mornings (Mon–Fri) so overnight news
is included before the LSE open (08:00).

Schedule (UK time):
  - RUN Monday 05:00    → Monday briefing (Friday's close + weekend news)
  - RUN Tue–Fri 05:00   → That day's briefing (previous session close)
  - SKIP Saturday/Sunday mornings (no LSE session)
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from config.loader import load_config

UK = ZoneInfo("Europe/London")

# Monday=0 … Sunday=6
_RUN_WEEKDAYS = frozenset({0, 1, 2, 3, 4})  # Mon–Fri mornings
_SKIP_WEEKDAYS = frozenset({5, 6})  # Sat, Sun

_DAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _uk_now(when: datetime | None = None) -> datetime:
    when = when or datetime.now(UK)
    if when.tzinfo is None:
        return when.replace(tzinfo=UK)
    return when.astimezone(UK)


def configured_run_hour_minute() -> tuple[int, int]:
    """Parse run_time_uk from config (default 05:00)."""
    config = load_config()
    raw = config.get("schedule", {}).get("run_time_uk", "05:00")
    parts = str(raw).split(":")
    hour = int(parts[0]) if parts else 5
    minute = int(parts[1]) if len(parts) > 1 else 0
    return hour, minute


def should_run_pipeline(when: datetime | None = None) -> bool:
    """True on Mon–Fri UK mornings (pipeline run days)."""
    when = _uk_now(when)
    return when.weekday() in _RUN_WEEKDAYS


def is_run_time_window(when: datetime | None = None, tolerance_minutes: int = 45) -> bool:
    """True if within tolerance of configured UK run time (for GitHub cron gating)."""
    when = _uk_now(when)
    hour, minute = configured_run_hour_minute()
    target = when.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delta_min = abs((when - target).total_seconds()) / 60
    return delta_min <= tolerance_minutes


def skip_reason(when: datetime | None = None) -> str:
    """Human-readable reason when should_run_pipeline is False."""
    when = _uk_now(when)
    day = _DAY_NAMES[when.weekday()]
    return (
        f"LSE closed — no pipeline on {day} morning. "
        f"Next run: Monday–Friday at 05:00 UK."
    )


def next_briefing_day(when: datetime | None = None) -> str:
    """Trading morning this run prepares data for (same calendar day at 05:00)."""
    when = _uk_now(when)
    return _DAY_NAMES[when.weekday()]
