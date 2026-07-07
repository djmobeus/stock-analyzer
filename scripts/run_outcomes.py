#!/usr/bin/env python3
"""Update 2/4/8-week outcomes for logged observations."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config.loader import load_env  # noqa: E402
from db.connection import init_database  # noqa: E402
from pipeline.nightly import setup_logging  # noqa: E402
from pipeline.outcomes import update_observation_outcomes  # noqa: E402


def main() -> int:
    load_env()
    init_database()
    setup_logging()
    summary = update_observation_outcomes()
    print("Outcome update:", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
