"""Track estimated API spend (Anthropic, etc.)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config.loader import load_config
from db.repositories import get_api_usage_summary, record_api_usage

logger = logging.getLogger(__name__)


def estimate_anthropic_cost_usd(
    input_tokens: int,
    output_tokens: int,
    model: str | None = None,
) -> float:
    """Estimate USD cost from token counts using config.yaml rates."""
    config = load_config()
    ac = config.get("anthropic", {})
    in_rate = float(ac.get("input_usd_per_mtok", 0.80))
    out_rate = float(ac.get("output_usd_per_mtok", 4.00))
    cost = (input_tokens / 1_000_000 * in_rate) + (output_tokens / 1_000_000 * out_rate)
    return round(cost, 6)


def log_anthropic_usage(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """Persist usage row; return estimated USD cost."""
    cost = estimate_anthropic_cost_usd(input_tokens, output_tokens, model)
    record_api_usage(
        provider="anthropic",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )
    logger.info(
        "Anthropic usage: in=%d out=%d est=$%.4f",
        input_tokens,
        output_tokens,
        cost,
    )
    return cost


def usage_display() -> dict:
    """Summary for dashboard: month, lifetime, GBP approx."""
    summary = get_api_usage_summary(provider="anthropic")
    gbp_rate = 0.79  # rough display conversion; not for billing
    return {
        **summary,
        "month_gbp": round(summary["month_usd"] * gbp_rate, 2),
        "lifetime_gbp": round(summary["lifetime_usd"] * gbp_rate, 2),
    }
