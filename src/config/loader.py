"""Load config.yaml and environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root is two levels above src/config/
ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"


def load_env() -> None:
    """Load .env from project root if present."""
    load_dotenv(ROOT_DIR / ".env")


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load and cache config.yaml."""
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_database_url() -> str | None:
    """Return DATABASE_URL or None for local SQLite default."""
    load_env()
    url = os.getenv("DATABASE_URL", "").strip()
    return url or None


def get_finnhub_api_key() -> str | None:
    """Return Finnhub API key if configured."""
    load_env()
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key or key == "your_key_here":
        return None
    return key
