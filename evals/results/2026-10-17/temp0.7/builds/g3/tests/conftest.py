"""Shared pytest fixtures."""

import sqlite3
import tempfile
import os
import uuid
import hashlib
import pytest

from reportkit.db      import apply_schema, get_connection
from reportkit.service import ReportService


@pytest.fixture()
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    apply_schema(path)
    return path


@pytest.fixture()
def conn(db_path):
    return get_connection(db_path)


@pytest.fixture()
def service(db_path, tmp_path):
    store: dict[str, bytes] = {}

    def mem_store(key: str, data: bytes) -> None:
        store[key] = data

    svc = ReportService(
        db_path,
        billing_secret=b"testsecret",
        attachment_store=mem_store,
    )
    svc._attachment_store_dict = store   # expose for assertions
    return svc


# ---------------------------------------------------------------------------
# Helpers to seed the DB directly
# ---------------------------------------------------------------------------

def make_tenant(conn, tenant_id=None, suspended=0) -> str:
    tid = tenant_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, suspended) VALUES (?, ?)", (tid, suspended)
    )
    conn.commit()
    return tid


def make_user(conn, tenant_id, role="editor", user_id=None) -> str:
    uid = user_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, ?)",
        (uid, tenant_id, role),
    )
    conn.commit()
    return uid


def make_session(conn, user_id, token=None, expires_offset="+1 hour") -> str:
    """Create a session and return the raw token."""
    raw = token or str(uuid.uuid4())
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    conn.execute(
        """
        INSERT INTO sessions (token_hash, user_id, expires_at)
             VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?))
        """,
        (token_hash, user_id, expires_offset),
    )
    conn.commit()
    return raw


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_report(conn, tenant_id, owner_id, title="Test Report", body="body") -> str:
    rid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO reports (id, tenant_id, owner_id, title, body) VALUES (?,?,?,?,?)",
        (rid, tenant_id, owner_id, title, body),
    )
    conn.commit()
    return rid
