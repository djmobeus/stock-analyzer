"""Database connection — SQLite locally, PostgreSQL (Supabase) in cloud."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from config.loader import ROOT_DIR, get_database_url

DEFAULT_SQLITE_PATH = ROOT_DIR / "data" / "stock_analyzer.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgres://")


def adapt_schema_for_postgres(sql: str) -> str:
    """Convert SQLite DDL to PostgreSQL-compatible DDL."""
    sql = re.sub(
        r"\bid\s+INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "id SERIAL PRIMARY KEY",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """
    Yield a database connection.

    Uses DATABASE_URL if set (Supabase), otherwise local SQLite.
    """
    url = get_database_url()
    if url and _is_postgres(url):
        import psycopg2

        conn = psycopg2.connect(url, connect_timeout=15)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_database() -> None:
    """Create tables from schema.sql."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    url = get_database_url()
    if url and _is_postgres(url):
        schema_sql = adapt_schema_for_postgres(schema_sql)

    with get_connection() as conn:
        cursor = conn.cursor()
        # Execute each statement (split on ;)
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)


def get_placeholder() -> str:
    """Return SQL parameter placeholder for active backend."""
    url = get_database_url()
    return "%s" if url and _is_postgres(url) else "?"
