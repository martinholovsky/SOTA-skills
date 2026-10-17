"""Shared test fixtures."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from reportkit.db import get_connection, init_schema
from reportkit.service import ReportService


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema applied."""
    c = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
    c.row_factory = lambda cur, row: {col[0]: row[i] for i, col in enumerate(cur.description)}
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    return c


@pytest.fixture()
def svc(conn: sqlite3.Connection) -> ReportService:
    return ReportService(conn)


def make_tenant(conn: sqlite3.Connection, *, suspended: bool = False) -> str:
    tid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, suspended) VALUES (?, ?)",
        (tid, 1 if suspended else 0),
    )
    return tid


def make_user(
    conn: sqlite3.Connection, tenant_id: str, role: str = "editor"
) -> tuple[str, str]:
    """Return (user_id, bearer_token)."""
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, ?)",
        (uid, tenant_id, role),
    )
    token = f"tok_{uuid.uuid4().hex}"
    expires = _iso(datetime.now(timezone.utc) + timedelta(hours=1))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), uid, expires),
    )
    return uid, token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_report(
    conn: sqlite3.Connection, tenant_id: str, owner_id: str, title: str = "My Report"
) -> str:
    rid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO reports (id, tenant_id, owner_id, title, body) VALUES (?, ?, ?, ?, ?)",
        (rid, tenant_id, owner_id, title, "body text"),
    )
    return rid
