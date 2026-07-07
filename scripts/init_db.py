#!/usr/bin/env python3
"""
Initialise the database schema.

Usage:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config.loader import load_env  # noqa: E402
from db.connection import DEFAULT_SQLITE_PATH, get_database_url, init_database  # noqa: E402


def main() -> int:
    load_env()
    url = get_database_url()
    if url:
        print(f"Initialising database (cloud): {url[:40]}...")
    else:
        print(f"Initialising database (local): {DEFAULT_SQLITE_PATH}")

    init_database()
    print("Database schema created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
