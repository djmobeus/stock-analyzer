"""Automated 2 / 4 / 8-week outcome tracking for observations."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from config.loader import load_config
from db.repositories import (
    get_observations,
    get_outcome_weeks,
    get_price_on_or_before,
    insert_outcome,
    upsert_pattern_stats,
)
from intelligence.patterns import PatternStat

logger = logging.getLogger(__name__)

OUTCOME_WEEKS = (2, 4, 8)


def _parse_observed_at(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _pct_change(entry: float, current: float) -> float:
    if entry <= 0:
        return 0.0
    return (current - entry) / entry * 100


def evaluate_flags(
    prediction: str,
    pct_change: float,
    target_hit_pct: float,
    stop_loss_pct: float,
) -> tuple[int, int, bool]:
    """
    Return (target_hit, stop_hit, correct).

    buy: target +8%, stop -5%
    watch: modest gain counts as hit
    avoid: correct if price did not rise meaningfully
    """
    target_hit = int(pct_change >= target_hit_pct)
    stop_hit = int(pct_change <= stop_loss_pct)

    if prediction == "buy":
        correct = pct_change >= target_hit_pct
    elif prediction == "watch":
        correct = pct_change >= target_hit_pct * 0.5
    else:  # avoid
        correct = pct_change < target_hit_pct * 0.5

    return target_hit, stop_hit, int(correct)


def update_observation_outcomes() -> dict:
    """Record missing 2/4/8-week outcomes for all observations."""
    config = load_config()
    oc = config.get("outcomes", {})
    target_hit_pct = float(oc.get("target_hit_pct", 8.0))
    stop_loss_pct = float(oc.get("stop_loss_pct", -5.0))
    today = date.today()

    recorded = 0
    skipped = 0

    for obs in get_observations():
        obs_id = int(obs["id"])
        observed_at = _parse_observed_at(obs["observed_at"])
        entry = obs.get("entry_price_gbx")
        if not entry or float(entry) <= 0:
            skipped += 1
            continue

        entry_f = float(entry)
        ticker = obs["ticker"]
        prediction = obs["prediction"]
        existing = set(get_outcome_weeks(obs_id))

        for weeks in OUTCOME_WEEKS:
            if weeks in existing:
                continue
            due = (observed_at + timedelta(weeks=weeks)).date()
            if today < due:
                continue

            price = get_price_on_or_before(ticker, due)
            if price is None:
                logger.warning("%s: no price for week %d outcome", ticker, weeks)
                skipped += 1
                continue

            pct = _pct_change(entry_f, price)
            target_hit, stop_hit, _ = evaluate_flags(
                prediction, pct, target_hit_pct, stop_loss_pct
            )
            insert_outcome(
                observation_id=obs_id,
                candidate_id=None,
                weeks=weeks,
                price_gbx=price,
                pct_change=round(pct, 2),
                target_hit=target_hit,
                stop_hit=stop_hit,
            )
            recorded += 1
            logger.info(
                "%s obs#%d week%d: %.1f%% (target_hit=%d)",
                ticker,
                obs_id,
                weeks,
                pct,
                target_hit,
            )

    stats_updated = recalculate_pattern_stats(target_hit_pct)
    shadow_summary = update_shadow_outcomes()
    return {
        "outcomes_recorded": recorded,
        "skipped": skipped,
        "pattern_types_updated": stats_updated,
        **shadow_summary,
    }


def update_shadow_outcomes() -> dict:
    """Record 2/4/8-week outcomes for shadow-logged candidates."""
    config = load_config()
    oc = config.get("outcomes", {})
    target_hit_pct = float(oc.get("target_hit_pct", 8.0))
    stop_loss_pct = float(oc.get("stop_loss_pct", -5.0))
    today = date.today()
    recorded = 0
    skipped = 0

    from db.repositories import (
        get_candidate_outcome_weeks,
        get_price_on_or_before,
        get_price_on_date,
        get_shadow_candidates_pending,
        insert_outcome,
    )

    for cand in get_shadow_candidates_pending():
        cand_id = int(cand["id"])
        scan_date = cand["scan_date"]
        if isinstance(scan_date, str):
            scan_date = date.fromisoformat(scan_date)
        ticker = cand["ticker"]
        entry = get_price_on_date(ticker, scan_date) or get_price_on_or_before(ticker, scan_date)
        if not entry or entry <= 0:
            skipped += 1
            continue

        existing = set(get_candidate_outcome_weeks(cand_id))
        for weeks in OUTCOME_WEEKS:
            if weeks in existing:
                continue
            due = scan_date + timedelta(weeks=weeks)
            if today < due:
                continue
            price = get_price_on_or_before(ticker, due)
            if price is None:
                skipped += 1
                continue
            pct = _pct_change(float(entry), price)
            target_hit = int(pct >= target_hit_pct)
            stop_hit = int(pct <= stop_loss_pct)
            insert_outcome(
                observation_id=None,
                candidate_id=cand_id,
                weeks=weeks,
                price_gbx=price,
                pct_change=round(pct, 2),
                target_hit=target_hit,
                stop_hit=stop_hit,
            )
            recorded += 1

    return {"shadow_outcomes_recorded": recorded, "shadow_skipped": skipped}


def recalculate_pattern_stats(target_hit_pct: float = 8.0) -> int:
    """
    Recompute rolling hit rates per pattern type from 8-week outcomes.

    Uses the primary pattern_key stored in features_json at log time.
    """
    from db.connection import get_connection, get_placeholder

    ph = get_placeholder()
    sql = f"""
        SELECT o.id, o.prediction, o.features_json, oc.pct_change, oc.target_hit
        FROM observations o
        JOIN outcomes oc ON oc.observation_id = o.id AND oc.weeks = 8
        WHERE o.features_json IS NOT NULL
    """
    buckets: dict[str, list[tuple[float, int]]] = {}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        for row in cur.fetchall():
            prediction = row[1]
            if prediction not in {"buy", "watch"}:
                continue
            try:
                features = json.loads(row[2] or "{}")
            except json.JSONDecodeError:
                continue
            key = features.get("pattern_key") or "unspecified"
            pct = float(row[3]) if row[3] is not None else 0.0
            hit = int(row[4] or 0)
            buckets.setdefault(key, []).append((pct, hit))

    for pattern_type, rows in buckets.items():
        sample_count = len(rows)
        hit_count = sum(h for _, h in rows)
        avg_gain = sum(p for p, _ in rows) / sample_count if sample_count else 0.0
        upsert_pattern_stats(
            PatternStat(
                pattern_type=pattern_type,
                sample_count=sample_count,
                hit_count=hit_count,
                avg_gain_pct=round(avg_gain, 2),
                avg_weeks=8.0,
            )
        )

    return len(buckets)
