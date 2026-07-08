"""Optional Anthropic Haiku morning prose summary."""

from __future__ import annotations

import logging
import os

from analysis.scoring import StockScore

logger = logging.getLogger(__name__)


def _template_summary(candidates: list[StockScore], briefing_for: str) -> str:
    if not candidates:
        return f"No candidates for {briefing_for}. Universe filters may have excluded all stocks."
    lines = [f"Morning scan for {briefing_for} — top {len(candidates)} candidates:\n"]
    for i, c in enumerate(candidates, 1):
        f = c.features
        dist = f.get("distance_support_pct")
        dist_s = f"{dist:.1f}%" if dist is not None else "n/a"
        target = f.get("analyst_target")
        target_s = f"{target:.0f}p" if target else "n/a"
        flags = " [MTF conflict]" if c.conflict_flag else ""
        lines.append(
            f"{i}. {c.ticker} (score {c.composite_score:.0f}) — "
            f"{dist_s} from support, confluence {f.get('confluence', 0)}/3, "
            f"analyst target {target_s}{flags}"
        )
    lines.append("\nAnalytical output only — not financial advice.")
    return "\n".join(lines)


def generate_morning_prose(candidates: list[StockScore], briefing_for: str) -> str:
    """Haiku summary when ANTHROPIC_API_KEY is set; otherwise template text."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _template_summary(candidates, briefing_for)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        facts = _template_summary(candidates, briefing_for)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a concise UK stock morning briefing (5–8 sentences) for a "
                        "self-directed investor. Use only the facts below. Do not give direct "
                        "buy/sell advice. Mention key levels and catalysts where present.\n\n"
                        f"{facts}"
                    ),
                }
            ],
        )
        text = message.content[0].text if message.content else ""
        usage = getattr(message, "usage", None)
        if usage:
            from intelligence.usage_tracking import log_anthropic_usage

            log_anthropic_usage(
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                model="claude-3-5-haiku-20241022",
            )
        return text.strip() or _template_summary(candidates, briefing_for)
    except Exception as exc:
        logger.warning("Anthropic summary failed (%s); using template", exc)
        return _template_summary(candidates, briefing_for)
