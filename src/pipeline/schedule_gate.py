"""Gate scheduled GitHub Actions runs to 05:00 UK and once per day."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from db.repositories import scan_completed_today
from pipeline.calendar import configured_run_hour_minute, is_run_time_window, should_run_pipeline, skip_reason

logger = logging.getLogger(__name__)
UK = ZoneInfo("Europe/London")


def should_run_scheduled_job(force: bool = False) -> tuple[bool, str]:
    """
    Decide if a scheduled cloud run should proceed.

    Returns (ok, reason).
    """
    if force:
        return True, "forced"

    if not should_run_pipeline():
        return False, skip_reason()

    if scan_completed_today():
        return False, "already_completed_today"

    # GitHub cron uses UTC; only enforce time window in CI
    if os.getenv("GITHUB_ACTIONS") == "true":
        if not is_run_time_window():
            now = datetime.now(UK)
            hour, minute = configured_run_hour_minute()
            return False, (
                f"outside_run_window (UK now {now.strftime('%H:%M')}, "
                f"target {hour:02d}:{minute:02d})"
            )

    return True, "ok"
