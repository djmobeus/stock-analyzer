"""Honest AI critique of the user's stock analysis."""

from __future__ import annotations

import logging
import os

from config.loader import load_config
from intelligence.usage_tracking import log_anthropic_usage

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a blunt UK equities coach for a retail self-directed investor. "
    "You are NOT a financial adviser and must not tell them to buy or sell. "
    "Be honest. Do not flatter. Challenge confirmation bias. "
    "Structure your reply with these headings exactly:\n"
    "## Correct because\n"
    "## Wrong or weak because\n"
    "## What could happen\n"
    "## What to check next\n"
    "Keep each section to 2–5 short bullets or sentences. Use only the facts provided."
)


def critique_user_analysis(
    *,
    ticker: str,
    company_name: str | None,
    why_bullets: list[str],
    user_notes: str,
    agree_with_system: str | None,
    features_summary: str,
) -> tuple[str, str]:
    """
    Returns (critique_text, source) where source is anthropic|template.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    name = company_name or ticker
    agree = agree_with_system or "not stated"
    facts = (
        f"Stock: {name} ({ticker})\n"
        f"User agrees with system shortlist rationale: {agree}\n"
        f"System why-chosen:\n" + "\n".join(f"- {b}" for b in why_bullets) + "\n"
        f"Features:\n{features_summary}\n"
        f"User analysis:\n{user_notes}\n"
    )
    if not api_key:
        return _template_critique(facts), "template"

    model = load_config().get("anthropic", {}).get("model", "claude-haiku-4-5-20251001")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=700,
            system=_SYSTEM,
            messages=[{"role": "user", "content": facts}],
        )
        text = message.content[0].text if message.content else ""
        usage = getattr(message, "usage", None)
        if usage:
            log_anthropic_usage(
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                model=model,
            )
        if text.strip():
            return text.strip(), "anthropic"
    except Exception as exc:
        logger.error("Coaching critique failed: %s", exc)
    return _template_critique(facts), "template"


def _template_critique(facts: str) -> str:
    return (
        "## Correct because\n"
        "- You engaged with the setup in writing — that is useful for learning.\n"
        "- Cross-check your notes against the system why-chosen bullets above.\n\n"
        "## Wrong or weak because\n"
        "- AI coaching is unavailable (no API key or call failed), so this is a template only.\n"
        "- Do not treat the shortlist score as a buy signal.\n\n"
        "## What could happen\n"
        "- Price can fail support; timeframe conflict (if flagged) often means choppy follow-through.\n\n"
        "## What to check next\n"
        "- Weekly chart trend, nearest catalyst date, and your stop distance in %.\n"
        f"\n<details><summary>Facts provided</summary>\n\n{facts}\n</details>"
    )
