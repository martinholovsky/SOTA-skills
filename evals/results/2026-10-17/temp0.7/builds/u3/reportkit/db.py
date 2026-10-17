"""Database helpers — connection factory and schema bootstrap."""
import sqlite3
import pathlib

_SCHEMA = pathlib.Path(__file__).with_name("schema.sql").read_text()


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Return a connection with row_factory and pragmas applied."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently apply the DDL."""
    conn.executescript(_SCHEMA)
    conn.commit()
