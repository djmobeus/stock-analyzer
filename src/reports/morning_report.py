"""Generate morning candidate report."""

from __future__ import annotations

import os
from datetime import date
from html import escape
from pathlib import Path

from analysis.scoring import StockScore
from config.loader import ROOT_DIR
from intelligence.ml_model import predict_probability
from visualization.links import research_links

REPORTS_DIR = ROOT_DIR / "reports"


def build_morning_report(
    candidates: list[StockScore],
    briefing_for: str,
    universe_size: int,
) -> str:
    """Build HTML morning report."""
    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<title>UK Stock Analyzer — Morning Scan</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:left}",
        "th{background:#f4f4f4}",
        ".conflict{color:#c00;font-weight:bold}",
        ".score{font-weight:bold}",
        ".why{font-size:0.9rem;margin:0.5rem 0 1.5rem;padding:0.75rem;background:#f8f8f8}",
        "</style></head><body>",
        f"<h1>Morning Scan — {date.today().isoformat()}</h1>",
        f"<p>Prepared for <strong>{escape(briefing_for)}</strong> | "
        f"Universe: {universe_size} stocks | Top candidates: {len(candidates)}</p>",
        "<p><em>Analytical output only — not financial advice. Prices from Yahoo/yfinance (GBX).</em></p>",
        "<table>",
        "<tr><th>#</th><th>Name</th><th>Ticker</th><th>Score</th><th>ML prob 8%+</th>"
        "<th>Support dist%</th><th>Timeframes</th><th>Flags</th></tr>",
    ]

    detail_blocks: list[str] = []

    for i, c in enumerate(candidates, 1):
        f = c.features
        why = f.get("why_chosen") or {}
        name = why.get("name") or f.get("company_name") or c.ticker
        flags = []
        if c.conflict_flag:
            flags.append('<span class="conflict">Timeframe conflict</span>')
        dist = f.get("distance_support_pct")
        dist_s = f"{dist:.1f}" if dist is not None else "—"
        ml = predict_probability(f)
        ml_s = f"{ml.probability:.0f}" if ml.probability is not None else "—"
        links = research_links(c.ticker)
        link = links["primary"]
        lines.append(
            f"<tr><td>{i}</td>"
            f"<td>{escape(str(name))}</td>"
            f"<td><a href='{escape(link)}' target='_blank' rel='noopener'>{escape(c.ticker)}</a></td>"
            f"<td class='score'>{c.composite_score:.1f}</td>"
            f"<td>{ml_s}</td>"
            f"<td>{dist_s}</td><td>{f.get('confluence', 0)} of 3</td>"
            f"<td>{' '.join(flags) or '—'}</td></tr>"
        )
        bullets = why.get("bullets") or []
        if bullets:
            lis = "".join(f"<li>{escape(b)}</li>" for b in bullets)
            detail_blocks.append(
                f"<h3>#{i} {escape(str(name))} ({escape(c.ticker)})</h3>"
                f"<div class='why'><ul>{lis}</ul>"
                f"<p><a href='{escape(link)}'>Open on {escape(links['primary_label'])}</a></p></div>"
            )

    lines.extend(
        [
            "</table>",
            "<h2>Why each stock was shortlisted</h2>",
            *detail_blocks,
            "<h2>What the numbers mean</h2>",
            "<ul>",
            "<li><strong>Score (0–100):</strong> Match to our rules today — not a guarantee.</li>",
            "<li><strong>ML prob 8%+:</strong> After ~100 outcomes; otherwise blank.</li>",
            "<li><strong>Timeframes:</strong> Daily / weekly / monthly bullish count.</li>",
            "<li><strong>Timeframe conflict:</strong> Daily bullish but weekly/monthly not.</li>",
            "</ul>",
        ]
    )
    app_url = (os.getenv("APP_BASE_URL") or "").rstrip("/")
    if app_url:
        lines.append(
            f"<p><strong>Open the app:</strong> "
            f"<a href='{escape(app_url)}/shortlist'>{escape(app_url)}/shortlist</a></p>"
        )
    lines.append("</body></html>")
    return "\n".join(lines)


def write_morning_report(
    candidates: list[StockScore],
    briefing_for: str,
    universe_size: int,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"morning_{date.today().isoformat()}.html"
    path.write_text(
        build_morning_report(candidates, briefing_for, universe_size),
        encoding="utf-8",
    )
    return path
