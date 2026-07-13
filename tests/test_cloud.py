"""Tests for schedule gate and email config."""

from unittest.mock import patch

from pipeline.schedule_gate import should_run_scheduled_job
from reports.email_digest import email_configured, get_email_config


def test_email_not_configured_by_default():
    with patch.dict("os.environ", {}, clear=True):
        assert email_configured() is False


def test_email_configured_when_set():
    env = {
        "SMTP_USER": "test@gmail.com",
        "SMTP_PASSWORD": "secret",
        "EMAIL_TO": "you@p-mouzakis.com",
    }
    with patch.dict("os.environ", env, clear=True):
        assert email_configured() is True
        assert get_email_config()["email_to"] == "you@p-mouzakis.com"


def test_force_bypasses_gate():
    ok, reason = should_run_scheduled_job(force=True)
    assert ok is True
    assert reason == "forced"


def test_late_github_run_still_proceeds():
    """GitHub cron delay past 05:00 must not skip the weekday job."""
    from datetime import datetime
    from unittest.mock import patch
    from zoneinfo import ZoneInfo

    UK = ZoneInfo("Europe/London")
    late = datetime(2026, 7, 13, 7, 47, tzinfo=UK)  # Monday 07:47
    with (
        patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}),
        patch("pipeline.schedule_gate.should_run_pipeline", return_value=True),
        patch("pipeline.schedule_gate.scan_completed_today", return_value=False),
        patch("pipeline.schedule_gate.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = late
        ok, reason = should_run_scheduled_job(force=False)
    assert ok is True
    assert "late_but_running" in reason
