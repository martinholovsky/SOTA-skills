"""Database helpers: connection factory and schema bootstrap."""

import sqlite3
import pathlib

_SCHEMA = pathlib.Path(__file__).with_name("schema.sql").read_text()

_ALLOWED_SORT_COLUMNS = frozenset({"created_at", "title"})


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Return a connection with row_factory and foreign-key enforcement."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently apply the DDL schema."""
    conn.executescript(_SCHEMA)


def validate_sort_column(column: str) -> str:
    """
    Return *column* if it is an allowed sort key, otherwise raise ValueError.

    This is the single place where user-supplied sort values are sanitised
    before being interpolated into SQL.  Parameterised queries cannot be used
    for column names, so an allowlist is the correct defence.
    """
    if column not in _ALLOWED_SORT_COLUMNS:
        raise ValueError(
            f"Invalid sort column {column!r}. "
            f"Allowed: {sorted(_ALLOWED_SORT_COLUMNS)}"
        )
    return column
