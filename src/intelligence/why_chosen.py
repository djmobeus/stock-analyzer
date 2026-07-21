"""Plain-English reasons a stock made the shortlist."""

from __future__ import annotations

from datetime import date, datetime, timezone

from db.connection import get_connection, get_placeholder


def _nearest_catalyst(ticker: str) -> dict | None:
    ph = get_placeholder()
    today = date.today().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT event_type, event_date, description
            FROM catalysts
            WHERE ticker = {ph} AND event_date >= {ph}
            ORDER BY event_date ASC
            LIMIT 1
            """,
            (ticker, today),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "event_type": row[0],
        "event_date": str(row[1])[:10] if row[1] else None,
        "description": row[2],
    }


def _company_name(ticker: str) -> str | None:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT name FROM stocks WHERE ticker = {ph}", (ticker,))
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def build_why_chosen(ticker: str, features: dict, composite_score: float) -> dict:
    """Structured explanation stored on the candidate."""
    bullets: list[str] = []
    dist = features.get("distance_support_pct")
    if dist is not None:
        try:
            dist_f = float(dist)
            if dist_f == dist_f:  # not NaN
                bullets.append(
                    f"Price is {dist_f:.1f}% from nearest support (closer is usually better)."
                )
        except (TypeError, ValueError):
            pass
    conf = features.get("confluence", 0) or 0
    bullets.append(
        f"Timeframes agree on {conf} of 3 (daily / weekly / monthly bullish rules)."
    )
    if features.get("conflict_flag"):
        bullets.append(
            "Caution: daily looks bullish but weekly and/or monthly does not (timeframe conflict)."
        )
    up = features.get("analyst_upside_score")
    if up is not None:
        bullets.append(f"Analyst-upside component scored {up:.0f}/100.")
    cat = features.get("catalyst_score") or 0
    catalyst = _nearest_catalyst(ticker)
    if catalyst and catalyst.get("event_date"):
        bullets.append(
            f"Upcoming catalyst: {catalyst.get('event_type') or 'event'} "
            f"around {catalyst['event_date']}"
            + (f" — {catalyst['description']}" if catalyst.get("description") else "")
            + "."
        )
    elif cat and cat >= 40:
        bullets.append(f"Catalyst timing component scored {cat:.0f}/100.")
    else:
        bullets.append("No clear dated catalyst in our news extract for the next few weeks.")
    sent = features.get("news_sentiment_score")
    if sent is not None:
        bullets.append(f"Recent news mood component scored {sent:.0f}/100.")
    regime = features.get("market_regime_score")
    if regime is not None:
        bullets.append(f"FTSE market-regime component scored {regime:.0f}/100.")
    bullets.append(
        f"Composite score {composite_score:.1f}/100 — ranked among stocks that passed filters today "
        "(not a guarantee of gain)."
    )

    return {
        "ticker": ticker,
        "name": _company_name(ticker),
        "composite_score": composite_score,
        "bullets": bullets,
        "catalyst": catalyst,
        "conflict": bool(features.get("conflict_flag")),
        "confluence": conf,
        "distance_support_pct": dist,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


def why_chosen_plain(why: dict) -> str:
    return "\n".join(f"• {b}" for b in why.get("bullets") or [])


def enrich_why_with_live_catalyst(ticker: str, why: dict) -> dict:
    """
    If stored why-chosen said no catalyst, but DB now has one, fix the bullets
    without waiting for tomorrow's rescore.
    """
    why = dict(why or {})
    bullets = list(why.get("bullets") or [])
    catalyst = _nearest_catalyst(ticker)
    if not catalyst or not catalyst.get("event_date"):
        return why
    live = (
        f"Upcoming catalyst: {catalyst.get('event_type') or 'event'} "
        f"around {catalyst['event_date']}"
        + (f" — {catalyst['description']}" if catalyst.get("description") else "")
        + "."
    )
    replaced = False
    new_bullets: list[str] = []
    for b in bullets:
        if "no clear dated catalyst" in b.lower() or (
            b.lower().startswith("upcoming catalyst:")
        ):
            new_bullets.append(live)
            replaced = True
        else:
            new_bullets.append(b)
    if not replaced:
        # Insert before the composite-score closing bullet if present
        if new_bullets and "composite score" in new_bullets[-1].lower():
            new_bullets.insert(-1, live)
        else:
            new_bullets.append(live)
    why["bullets"] = new_bullets
    why["catalyst"] = catalyst
    return why
