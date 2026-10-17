"""Database helpers — connection factory and schema bootstrap."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_local = threading.local()

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a per-thread connection to *db_path*, creating it if needed."""
    key = f"conn_{db_path}"
    conn = getattr(_local, key, None)
    if conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        conn.row_factory = _row_factory
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        setattr(_local, key, conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply the DDL (idempotent)."""
    conn.executescript(_SCHEMA)
