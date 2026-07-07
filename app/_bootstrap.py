"""Add src/ to path and load environment for Streamlit pages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config.loader import load_env  # noqa: E402
from db.connection import init_database  # noqa: E402


def bootstrap() -> None:
    load_env()
    init_database()
