"""Gate scheduled GitHub Actions runs — once per weekday morning."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from db.repositories import scan_completed_today
from pipeline.calendar import (
    configured_run_hour_minute,
    is_morning_delivery_window,
    should_run_pipeline,
    skip_reason,
)

logger = logging.getLogger(__name__)
UK = ZoneInfo("Europe/London")


def should_run_scheduled_job(force: bool = False) -> tuple[bool, str]:
    """
    Decide if a scheduled cloud run should proceed.

    Returns (ok, reason).

    Scheduled runs (GitHub Actions) only skip weekends / non-run days and
    ``already_completed_today``. They do **not** skip for being late —
    GitHub cron often starts 30–120 minutes after the scheduled time.
    """
    if force:
        return True, "forced"

    if not should_run_pipeline():
        return False, skip_reason()

    if scan_completed_today():
        return False, "already_completed_today"

    now = datetime.now(UK)
    hour, minute = configured_run_hour_minute()
    target = f"{hour:02d}:{minute:02d}"

    if os.getenv("GITHUB_ACTIONS") == "true":
        if is_morning_delivery_window(now):
            return True, f"ok (UK {now.strftime('%H:%M')}, target {target})"
        # Still run — better late email than no email — but log clearly
        logger.warning(
            "Starting after the usual morning window (UK now %s, preferred %s). "
            "GitHub cron delay is common; continuing so you still get a briefing.",
            now.strftime("%H:%M"),
            target,
        )
        return True, f"late_but_running (UK {now.strftime('%H:%M')}, target {target})"

    return True, "ok"
