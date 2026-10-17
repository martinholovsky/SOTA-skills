"""Database helpers: connection factory and schema bootstrap."""

import sqlite3
import pathlib
import threading

_local = threading.local()
_SCHEMA = pathlib.Path(__file__).with_name("schema.sql").read_text()


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return a per-thread SQLite connection.

    WAL mode and foreign keys are enforced here so every connection
    gets them regardless of how it was opened.
    """
    conn = getattr(_local, "conn", None)
    # Re-open if the path changed (tests use different paths per run).
    if conn is None or getattr(_local, "db_path", None) != db_path:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
        _local.db_path = db_path
    return conn


def apply_schema(db_path: str) -> None:
    """Create all tables if they do not yet exist."""
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
