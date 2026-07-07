"""Post-scan delivery — prose summary and email digest."""

from __future__ import annotations

import logging
from datetime import date
from html import escape
from pathlib import Path

from analysis.scoring import StockScore
from intelligence.morning_brief import generate_morning_prose
from reports.email_digest import send_morning_email

logger = logging.getLogger(__name__)


def deliver_morning_briefing(
    shortlist: list[StockScore],
    briefing_for: str,
    report_path: str | Path,
    universe_size: int,
) -> dict:
    """Generate prose summary and send email digest."""
    report_path = Path(report_path)
    prose = generate_morning_prose(shortlist, briefing_for)

    # Append prose to HTML report
    if report_path.exists():
        html = report_path.read_text(encoding="utf-8")
        block = (
            f"<h2>Morning summary</h2><pre style='white-space:pre-wrap;font-family:inherit'>"
            f"{escape(prose)}</pre>"
        )
        html = html.replace("</body>", f"{block}</body>")
        report_path.write_text(html, encoding="utf-8")

    subject = f"UK Stock Analyzer — {briefing_for} ({date.today().isoformat()})"
    plain = (
        f"{prose}\n\n"
        f"Universe: {universe_size} stocks | Top candidates: {len(shortlist)}\n"
        f"Full report attached as HTML.\n"
    )
    email_result = send_morning_email(subject, plain, html_report_path=report_path)
    logger.info("Delivery: %s", email_result)
    return {"morning_prose": prose[:200] + "...", **email_result}
