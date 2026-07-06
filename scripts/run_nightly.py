#!/usr/bin/env python3
"""
Nightly pipeline entry point.

Runs the full stock screening batch: prices, indicators, fundamentals,
news, scoring, shadow logging, and morning report generation.

Usage:
    python scripts/run_nightly.py

Scheduled via GitHub Actions on weekdays at 17:30 UK, or locally via
Task Scheduler / manual run.
"""

import sys
from pathlib import Path

# Allow imports from src/ before package is fully scaffolded
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    print("UK Stock Analyzer — nightly pipeline")
    print("Status: not yet implemented (Phase 1)")
    print("See docs/tasks.md for development roadmap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
