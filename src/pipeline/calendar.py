"""
UK market schedule for the morning pipeline.

Preferred start: 05:00 UK Mon–Fri (overnight news in, results aimed before 07:00).
GitHub Actions cron is often delayed; the schedule gate still runs late weekday
jobs instead of skipping them.

Schedule (UK time):
  - RUN Mon–Fri mornings → that day's briefing
  - SKIP Saturday/Sunday
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


def results_by_hour_uk() -> int:
    """Preferred latest hour (UK) for email delivery — default 7."""
    config = load_config()
    return int(config.get("schedule", {}).get("results_by_hour_uk", 7))


def should_run_pipeline(when: datetime | None = None) -> bool:
    """True on Mon–Fri UK mornings (pipeline run days)."""
    when = _uk_now(when)
    return when.weekday() in _RUN_WEEKDAYS


def is_run_time_window(when: datetime | None = None, tolerance_minutes: int = 45) -> bool:
    """True if within tolerance of configured UK run time (legacy helper)."""
    when = _uk_now(when)
    hour, minute = configured_run_hour_minute()
    target = when.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delta_min = abs((when - target).total_seconds()) / 60
    return delta_min <= tolerance_minutes


def is_morning_delivery_window(when: datetime | None = None) -> bool:
    """
    True if we are still in the preferred morning delivery window.

    From preferred run time through ``results_by_hour_uk`` (default 07:00).
    Used for logging only — late weekday runs still proceed.
    """
    when = _uk_now(when)
    hour, minute = configured_run_hour_minute()
    start = when.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end = when.replace(hour=results_by_hour_uk(), minute=0, second=0, microsecond=0)
    return start <= when <= end


def skip_reason(when: datetime | None = None) -> str:
    """Human-readable reason when should_run_pipeline is False."""
    when = _uk_now(when)
    day = _DAY_NAMES[when.weekday()]
    hour, minute = configured_run_hour_minute()
    return (
        f"LSE closed — no pipeline on {day} morning. "
        f"Next run: Monday–Friday around {hour:02d}:{minute:02d} UK "
        f"(results aimed by {results_by_hour_uk():02d}:00)."
    )


def next_briefing_day(when: datetime | None = None) -> str:
    """Trading morning this run prepares data for (same calendar day)."""
    when = _uk_now(when)
    return _DAY_NAMES[when.weekday()]
