"""Morning email digest via SMTP (Gmail-compatible)."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)


def get_email_config() -> dict:
    """Load email settings from environment."""
    return {
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", "").strip(),
        "smtp_password": os.getenv("SMTP_PASSWORD", "").strip(),
        "email_from": os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", "")).strip(),
        "email_to": os.getenv("EMAIL_TO", "").strip(),
    }


def email_configured() -> bool:
    cfg = get_email_config()
    return bool(cfg["smtp_user"] and cfg["smtp_password"] and cfg["email_to"])


def send_morning_email(
    subject: str,
    plain_body: str,
    html_report_path: Path | None = None,
) -> dict:
    """
    Send morning digest to EMAIL_TO.

    Returns status dict. Does not raise if email is not configured.
    """
    cfg = get_email_config()
    if not email_configured():
        logger.info("Email not configured — skip send (set SMTP_USER, SMTP_PASSWORD, EMAIL_TO)")
        return {"email_status": "skipped", "reason": "not_configured"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["email_from"]
    msg["To"] = cfg["email_to"]

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))

    if html_report_path and html_report_path.exists():
        html = html_report_path.read_text(encoding="utf-8")
        msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(cfg["email_from"], [cfg["email_to"]], msg.as_string())
        logger.info("Morning email sent to %s", cfg["email_to"])
        return {"email_status": "sent", "email_to": cfg["email_to"]}
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return {"email_status": "failed", "error": str(exc)}
