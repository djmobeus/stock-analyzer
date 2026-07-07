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
