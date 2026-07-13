#!/usr/bin/env python3
"""
Nightly stock screening pipeline entry point.

Usage:
    python scripts/run_nightly.py
    python scripts/run_nightly.py --limit 5   # test on 5 stocks
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pipeline.nightly import run_nightly_pipeline, setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="UK Stock Analyzer nightly pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Process only N stocks (testing)")
    parser.add_argument("--force", action="store_true", help="Run even on Fri/Sat (testing)")
    args = parser.parse_args()

    setup_logging()
    summary = run_nightly_pipeline(limit=args.limit, force=args.force)
    print("\n--- Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    # Make skips obvious in GitHub Actions UI (search for SKIPPED)
    if summary.get("status") == "skipped":
        print(f"\nSKIPPED: {summary.get('reason', 'unknown')}")
        return 0
    return 0 if summary.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
