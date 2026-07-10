"""Generate morning candidate report."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from config.loader import ROOT_DIR
from analysis.scoring import StockScore
from intelligence.ml_model import predict_probability
from visualization.charts import investing_url

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
        "</style></head><body>",
        f"<h1>Morning Scan — {date.today().isoformat()}</h1>",
        f"<p>Prepared for <strong>{briefing_for}</strong> | "
        f"Universe: {universe_size} stocks | Top candidates: {len(candidates)}</p>",
        "<p><em>Analytical output only — not financial advice.</em></p>",
        "<table>",
        "<tr><th>#</th><th>Ticker</th><th>Score</th><th>ML prob 8%+</th><th>Support dist%</th>"
        "<th>Timeframes agree</th><th>Analyst target</th><th>Flags</th></tr>",
    ]

    for i, c in enumerate(candidates, 1):
        f = c.features
        flags = []
        if c.conflict_flag:
            flags.append('<span class="conflict">Timeframe conflict</span>')
        dist = f.get("distance_support_pct")
        dist_s = f"{dist:.1f}" if dist is not None else "—"
        target = f.get("analyst_target")
        target_s = f"{target:.0f}p" if target else "—"
        ml = predict_probability(f)
        ml_s = f"{ml.probability:.0f}" if ml.probability is not None else "—"
        link = investing_url(c.ticker)
        lines.append(
            f"<tr><td>{i}</td>"
            f"<td><a href='{link}' target='_blank' rel='noopener'>{c.ticker}</a></td>"
            f"<td class='score'>{c.composite_score:.1f}</td>"
            f"<td>{ml_s}</td>"
            f"<td>{dist_s}</td><td>{f.get('confluence', 0)} of 3</td>"
            f"<td>{target_s}</td><td>{' '.join(flags) or '—'}</td></tr>"
        )

    lines.extend(
        [
            "</table>",
            "<h2>What the numbers mean</h2>",
            "<ul>",
            "<li><strong>Score (0–100):</strong> How well the stock matches our rules today "
            "(support, timeframes, analysts, catalysts, news, market). "
            "50–60 is common — these are the best of today's filtered list, not guaranteed winners.</li>",
            "<li><strong>ML prob 8%+:</strong> Chance of +8% within 8 weeks — shows when we have "
            "~100 completed outcomes. Otherwise blank.</li>",
            "<li><strong>Timeframes agree (0–3):</strong> How many of daily / weekly / monthly "
            "charts look bullish on our rules.</li>",
            "<li><strong>Timeframe conflict:</strong> Daily looks bullish but weekly or monthly "
            "does not — treat as a caution.</li>",
            "</ul>",
            "</body></html>",
        ]
    )
    return "\n".join(lines)


def write_morning_report(
    candidates: list[StockScore],
    briefing_for: str,
    universe_size: int,
) -> Path:
    """Write HTML report to reports/ directory."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"morning_{date.today().isoformat()}.html"
    path.write_text(
        build_morning_report(candidates, briefing_for, universe_size),
        encoding="utf-8",
    )
    return path
