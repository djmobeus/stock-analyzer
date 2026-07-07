"""Walk-forward backtest on historical shadow candidates."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config.loader import ROOT_DIR, load_config
from db.connection import get_connection, get_placeholder
from db.repositories import get_price_on_or_before

logger = logging.getLogger(__name__)
REPORTS_DIR = ROOT_DIR / "reports"


@dataclass
class BacktestTrade:
    ticker: str
    scan_date: date
    rank: int
    composite_score: float
    entry_gbx: float
    exit_gbx: float
    pct_change: float
    target_hit: bool
    stop_hit: bool


@dataclass
class BacktestSummary:
    trades: list[BacktestTrade]
    hit_rate_pct: float
    avg_return_pct: float
    sample_count: int


def _load_historical_candidates() -> list[dict]:
    ph = get_placeholder()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT scan_date, ticker, rank, composite_score, features_json
            FROM candidates
            ORDER BY scan_date ASC, rank ASC
            """
        )
        rows = cur.fetchall()
    return [
        {
            "scan_date": date.fromisoformat(str(r[0])) if not isinstance(r[0], date) else r[0],
            "ticker": r[1],
            "rank": r[2],
            "composite_score": r[3],
            "features_json": r[4],
        }
        for r in rows
    ]


def run_backtest(hold_weeks: int = 8, top_n: int = 10) -> BacktestSummary:
    """
    Backtest shadow candidates: entry at scan-date close, exit at hold_weeks.
    """
    config = load_config()
    oc = config.get("outcomes", {})
    target_hit_pct = float(oc.get("target_hit_pct", 8.0))
    stop_loss_pct = float(oc.get("stop_loss_pct", -5.0))
    today = date.today()

    by_date: dict[date, list[dict]] = {}
    for row in _load_historical_candidates():
        by_date.setdefault(row["scan_date"], []).append(row)

    trades: list[BacktestTrade] = []
    for scan_date, cands in sorted(by_date.items()):
        exit_date = scan_date + timedelta(weeks=hold_weeks)
        if exit_date > today:
            continue
        for c in sorted(cands, key=lambda x: x["rank"])[:top_n]:
            ticker = c["ticker"]
            entry = get_price_on_or_before(ticker, scan_date)
            exit_px = get_price_on_or_before(ticker, exit_date)
            if not entry or not exit_px or entry <= 0:
                continue
            pct = (exit_px - entry) / entry * 100
            trades.append(
                BacktestTrade(
                    ticker=ticker,
                    scan_date=scan_date,
                    rank=int(c["rank"]),
                    composite_score=float(c["composite_score"] or 0),
                    entry_gbx=round(entry, 2),
                    exit_gbx=round(exit_px, 2),
                    pct_change=round(pct, 2),
                    target_hit=pct >= target_hit_pct,
                    stop_hit=pct <= stop_loss_pct,
                )
            )

    n = len(trades)
    hits = sum(1 for t in trades if t.target_hit)
    avg = sum(t.pct_change for t in trades) / n if n else 0.0
    return BacktestSummary(
        trades=trades,
        hit_rate_pct=round(hits / n * 100, 1) if n else 0.0,
        avg_return_pct=round(avg, 2),
        sample_count=n,
    )


def write_backtest_report(summary: BacktestSummary) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"backtest_{date.today().isoformat()}.md"
    lines = [
        f"# Backtest Report — {date.today().isoformat()}",
        "",
        f"- Trades: {summary.sample_count}",
        f"- Hit rate (≥8%): {summary.hit_rate_pct}%",
        f"- Avg return: {summary.avg_return_pct:+.2f}%",
        "",
        "| Scan | Ticker | Rank | Score | Entry | Exit | Return % | Hit |",
        "|------|--------|------|-------|-------|------|----------|-----|",
    ]
    for t in summary.trades[-50:]:
        lines.append(
            f"| {t.scan_date} | {t.ticker} | {t.rank} | {t.composite_score:.1f} | "
            f"{t.entry_gbx:.0f}p | {t.exit_gbx:.0f}p | {t.pct_change:+.1f}% | "
            f"{'✓' if t.target_hit else '—'} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
