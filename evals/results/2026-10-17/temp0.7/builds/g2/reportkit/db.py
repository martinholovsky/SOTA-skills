"""Database helpers — connection factory and migration bootstrap."""

import sqlite3
import pathlib
import threading

_local = threading.local()

SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return a per-thread SQLite connection.

    Each connection:
    - uses WAL mode (set in schema)
    - enforces foreign keys
    - returns rows as dicts
    - sets a 5-second busy timeout to avoid SQLITE_BUSY under concurrent WAL writes
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=5.0)
        conn.row_factory = _row_factory
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return conn


def init_db(db_path: str) -> None:
    """Create schema if it does not exist."""
    conn = get_connection(db_path)
    sql = SCHEMA_PATH.read_text()
    conn.executescript(sql)
    conn.commit()
