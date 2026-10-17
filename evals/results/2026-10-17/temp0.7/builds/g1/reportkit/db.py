"""Database helpers: connection factory, migration, query utilities."""

import sqlite3
import os
import pathlib
import logging

logger = logging.getLogger(__name__)

_SCHEMA = pathlib.Path(__file__).with_name("schema.sql").read_text()


def connect(db_path: str) -> sqlite3.Connection:
    """Return a connection with recommended settings applied."""
    conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # Enforce FK constraints and WAL on every new connection.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently apply the DDL schema."""
    conn.executescript(_SCHEMA)


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)
