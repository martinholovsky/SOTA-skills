"""Shared pytest fixtures."""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from reportkit.db import apply_schema, connect
from reportkit.events import clear_all_handlers
from reportkit.service import ReportService


WEBHOOK_SECRET = b"test-webhook-secret-32-bytes-long!!"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture()
def conn():
    """In-memory SQLite connection with schema applied."""
    c = connect(":memory:")
    apply_schema(c)
    yield c
    c.close()


@pytest.fixture()
def service(conn):
    clear_all_handlers()
    return ReportService(conn, webhook_secret=WEBHOOK_SECRET)


@pytest.fixture()
def tenant_id():
    return "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"


@pytest.fixture()
def other_tenant_id():
    return "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"


def _make_user(conn, tenant_id, role="editor", uid=None):
    uid = uid or secrets.token_hex(8) + "-0000-4000-8000-" + secrets.token_hex(6)
    # Normalise to proper UUID format for fixture convenience.
    uid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" if uid == "default" else uid
    conn.execute(
        "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
        (tenant_id, "Test Tenant"),
    )
    conn.execute(
        "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
        (uid, tenant_id, f"user_{uid[:4]}", role),
    )
    return uid


def _make_session(conn, user_id):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), user_id, expires),
    )
    return token


def make_request(token: str, body: dict | None = None, query: dict | None = None,
                 remote_addr: str = "127.0.0.1") -> dict:
    return {
        "headers":     {"Authorization": f"Bearer {token}"},
        "body":        body or {},
        "query":       query or {},
        "remote_addr": remote_addr,
    }


@pytest.fixture()
def editor(conn, tenant_id):
    uid = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _make_user(conn, tenant_id, role="editor", uid=uid)
    token = _make_session(conn, uid)
    return {"user_id": uid, "token": token, "tenant_id": tenant_id}


@pytest.fixture()
def viewer(conn, tenant_id):
    uid = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    _make_user(conn, tenant_id, role="viewer", uid=uid)
    token = _make_session(conn, uid)
    return {"user_id": uid, "token": token, "tenant_id": tenant_id}


@pytest.fixture()
def admin(conn, tenant_id):
    uid = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    _make_user(conn, tenant_id, role="admin", uid=uid)
    token = _make_session(conn, uid)
    return {"user_id": uid, "token": token, "tenant_id": tenant_id}


@pytest.fixture()
def other_editor(conn, other_tenant_id):
    uid = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    _make_user(conn, other_tenant_id, role="editor", uid=uid)
    token = _make_session(conn, uid)
    return {"user_id": uid, "token": token, "tenant_id": other_tenant_id}
