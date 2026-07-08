#!/usr/bin/env python3
"""Send a test email using SMTP settings from .env."""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config.loader import load_env  # noqa: E402
from reports.email_digest import email_configured, get_email_config, send_morning_email  # noqa: E402


def main() -> int:
    load_env()
    cfg = get_email_config()

    if not email_configured():
        print("Email not configured. Set in .env:")
        print("  SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO")
        return 1

    print(f"Sending test email...")
    print(f"  From: {cfg['email_from']}")
    print(f"  To:   {cfg['email_to']}")
    print(f"  Host: {cfg['smtp_host']}:{cfg['smtp_port']}")

    body = (
        f"UK Stock Analyzer — test email\n\n"
        f"If you received this, SMTP is working.\n"
        f"Sender (Gmail): {cfg['email_from']}\n"
        f"Receiver: {cfg['email_to']}\n"
        f"Sent at: {datetime.now().isoformat(timespec='seconds')}\n"
    )
    result = send_morning_email(
        subject="UK Stock Analyzer — test email",
        plain_body=body,
    )
    print("Result:", result)
    return 0 if result.get("email_status") == "sent" else 1


if __name__ == "__main__":
    raise SystemExit(main())
