"""Shared bootstrap for the webapp."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.loader import load_env  # noqa: E402
from db.connection import init_database  # noqa: E402

_ready = False


def ensure_ready() -> None:
    global _ready
    if _ready:
        return
    load_env()
    init_database()
    _ready = True


def app_password() -> str:
    return os.getenv("APP_PASSWORD", "").strip()
