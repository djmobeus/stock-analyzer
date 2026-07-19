"""Database connection — SQLite locally, PostgreSQL (Supabase) in cloud."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from config.loader import ROOT_DIR, get_database_url

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = ROOT_DIR / "data" / "stock_analyzer.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_local = threading.local()


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


def _get_pg_connection(url: str):
    """Reuse one Postgres connection per thread (avoids ~2s SSL handshake each query)."""
    import psycopg2

    conn = getattr(_local, "pg_conn", None)
    if conn is not None and getattr(conn, "closed", 1) == 0:
        try:
            # Cheap liveness check
            conn.cursor().execute("SELECT 1")
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            _local.pg_conn = None

    conn = psycopg2.connect(
        url,
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )
    _local.pg_conn = conn
    return conn


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """
    Yield a database connection.

    Uses DATABASE_URL if set (Supabase), otherwise local SQLite.
    Postgres connections are reused per thread.
    """
    url = get_database_url()
    if url and _is_postgres(url):
        conn = _get_pg_connection(url)
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
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
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)


def get_placeholder() -> str:
    """Return SQL parameter placeholder for active backend."""
    url = get_database_url()
    return "%s" if url and _is_postgres(url) else "?"
