"""
Database helpers.

All queries use parameterised statements.  Identifiers that must be
interpolated (ORDER BY column) are mapped through a hard-coded allowlist.
"""

import sqlite3
import os
from pathlib import Path


def open_db(path: str = ":memory:") -> sqlite3.Connection:
    """
    Open (or create) the SQLite database and apply the schema.

    WAL mode and foreign-key enforcement are set on every connection.
    Row factory is set so callers get dict-like rows.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text())
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Allowlisted sort columns for ORDER BY injection prevention (rules/01 §2).
# Maps the user-visible name to the exact SQL column expression.
# ---------------------------------------------------------------------------
REPORT_SORT_COLUMNS: dict[str, str] = {
    "created_at": "created_at",
    "title": "title",
}

DEFAULT_SORT_COLUMN = "created_at"
