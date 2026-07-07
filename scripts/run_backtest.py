#!/usr/bin/env python3
"""Run walk-forward backtest on shadow candidates."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from analysis.backtest import run_backtest, write_backtest_report  # noqa: E402
from config.loader import load_env  # noqa: E402
from db.connection import init_database  # noqa: E402


def main() -> int:
    load_env()
    init_database()
    summary = run_backtest()
    path = write_backtest_report(summary)
    print(f"Backtest: {summary.sample_count} trades, hit rate {summary.hit_rate_pct}%")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
