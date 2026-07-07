#!/usr/bin/env python3
"""
Phase 0 — Validate yfinance LSE data on 30 representative tickers.

Usage:
    python scripts/run_phase0_validation.py

Writes docs/phase0_report.md with results.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config.loader import get_finnhub_api_key, load_config, load_env  # noqa: E402
from data.finnhub_client import finnhub_close_gbx  # noqa: E402
from data.prices import fetch_ohlcv, fetch_ticker_metadata  # noqa: E402
from data.quality import QualityReport, check_price_quality, compare_with_reference  # noqa: E402
from db.connection import init_database  # noqa: E402
from db.repositories import save_quality_flag  # noqa: E402

TICKERS_CSV = ROOT / "data" / "validation_tickers.csv"
REPORT_PATH = ROOT / "docs" / "phase0_report.md"


@dataclass
class ValidationRow:
    ticker: str
    sector: str
    currency: str | None
    close_gbx: float | None
    last_date: date | None
    passed: bool
    quarantined: bool
    flags: list[str] = field(default_factory=list)
    finnhub_close: float | None = None
    finnhub_match: bool | None = None
    finnhub_diff_pct: float | None = None


def load_validation_tickers() -> pd.DataFrame:
    return pd.read_csv(TICKERS_CSV)


def validate_ticker(ticker: str, dq_config: dict) -> ValidationRow:
    """Fetch, normalise, and quality-check one ticker."""
    meta = fetch_ticker_metadata(ticker)
    currency = meta.get("currency")

    result = fetch_ohlcv(ticker)
    report = check_price_quality(
        result,
        max_daily_jump_pct=dq_config.get("max_daily_jump_pct", 25.0),
        stale_days=dq_config.get("stale_days", 5),
        min_price_gbx=dq_config.get("min_price_gbx", 1.0),
        max_price_gbx=dq_config.get("max_price_gbx", 500_000.0),
    )

    row = ValidationRow(
        ticker=ticker,
        sector="",
        currency=currency,
        close_gbx=report.latest_close_gbx,
        last_date=report.last_date,
        passed=report.passed,
        quarantined=report.quarantine,
        flags=report.flags,
    )

    # Finnhub cross-check when API key available
    if get_finnhub_api_key() and report.latest_close_gbx:
        fh_close = finnhub_close_gbx(ticker)
        row.finnhub_close = fh_close
        if fh_close:
            match, diff = compare_with_reference(report.latest_close_gbx, fh_close, tolerance_pct=2.0)
            row.finnhub_match = match
            row.finnhub_diff_pct = round(diff, 2)
            if not match and diff > 5.0:
                row.flags.append(f"finnhub_mismatch_{diff:.1f}pct")
                row.quarantined = True
                row.passed = False

    # Persist flags to database
    if report.flags or report.quarantine:
        for flag in report.flags:
            save_quality_flag(
                ticker=ticker,
                flag_date=date.today(),
                flag_type=flag[:50],
                details="; ".join(report.flags),
                quarantined=report.quarantine,
            )
            break  # one row per ticker per day is enough

    return row


def build_report(rows: list[ValidationRow], tickers_df: pd.DataFrame) -> str:
    sector_map = dict(zip(tickers_df["ticker"], tickers_df["sector"]))
    for r in rows:
        r.sector = sector_map.get(r.ticker, "")

    total = len(rows)
    quarantined = sum(1 for r in rows if r.quarantined)
    passed = sum(1 for r in rows if r.passed)
    fh_checked = [r for r in rows if r.finnhub_match is not None]
    fh_matched = sum(1 for r in fh_checked if r.finnhub_match)
    fh_fail = len(fh_checked) - fh_matched

    error_rate = (quarantined / total * 100) if total else 0
    fh_error_rate = (fh_fail / len(fh_checked) * 100) if fh_checked else None

    lines = [
        "# Phase 0 — Data Validation Report",
        "",
        f"**Date:** {date.today().isoformat()}",
        f"**Tickers tested:** {total}",
        f"**Passed quality checks:** {passed}",
        f"**Quarantined:** {quarantined}",
        f"**Quarantine rate:** {error_rate:.1f}%",
        "",
        "**Exit criterion:** <2% quarantine rate on validation set.",
        f"**Result:** {'PASS' if error_rate < 2.0 else 'REVIEW NEEDED'}",
        "",
    ]

    if fh_checked:
        lines.extend([
            "## Finnhub cross-check",
            "",
            f"- Tickers compared: {len(fh_checked)}",
            f"- Within 2% tolerance: {fh_matched}",
            f"- Mismatch rate: {fh_error_rate:.1f}%",
            "",
        ])

    lines.extend([
        "## Per-ticker results",
        "",
        "| Ticker | Sector | Currency | Close (GBX) | Last date | Status | Flags |",
        "|--------|--------|----------|-------------|-----------|--------|-------|",
    ])

    for r in rows:
        status = "OK" if r.passed else "QUARANTINE"
        flags = ", ".join(r.flags[:3]) if r.flags else "—"
        close = f"{r.close_gbx:.2f}" if r.close_gbx else "—"
        ld = r.last_date.isoformat() if r.last_date else "—"
        lines.append(f"| {r.ticker} | {r.sector} | {r.currency or '?'} | {close} | {ld} | {status} | {flags} |")

    lines.extend([
        "",
        "## Notes",
        "",
        "- Prices normalised to GBX (pence) internally.",
        "- `repair=True` is NOT used on yfinance (can corrupt GBp data).",
        "- Add FINNHUB_API_KEY to `.env` for cross-validation.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    load_env()
    config = load_config()
    dq = config.get("data_quality", {})

    print("Phase 0: LSE price data validation")
    print("=" * 40)

    init_database()
    tickers_df = load_validation_tickers()
    tickers = tickers_df["ticker"].tolist()

    rows: list[ValidationRow] = []
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker}...", end=" ", flush=True)
        try:
            row = validate_ticker(ticker, dq)
            rows.append(row)
            status = "OK" if row.passed else "QUARANTINE"
            print(status)
        except Exception as exc:
            print(f"ERROR: {exc}")
            rows.append(
                ValidationRow(
                    ticker=ticker,
                    sector="",
                    currency=None,
                    close_gbx=None,
                    last_date=None,
                    passed=False,
                    quarantined=True,
                    flags=[f"fetch_error: {exc}"],
                )
            )

    report = build_report(rows, tickers_df)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")

    quarantined = sum(1 for r in rows if r.quarantined)
    rate = quarantined / len(rows) * 100 if rows else 0
    print(f"Quarantine rate: {rate:.1f}% ({quarantined}/{len(rows)})")
    return 0 if rate < 2.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
