"""
Shared test fixtures.

Uses an in-memory SQLite database so tests are isolated and fast.
"""

import pytest
import sqlite3
import time
import uuid

from reportkit.db import init_db, _row_factory
from reportkit.crypto import hash_token, generate_token
from reportkit.service import ReportService


DB_PATH = ":memory:"


@pytest.fixture()
def db():
    """Fresh in-memory database, schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA foreign_keys = ON")
    import pathlib
    schema = (pathlib.Path(__file__).parent.parent / "reportkit" / "schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()
    return conn


def _make_user(db, role="viewer", tenant_id=None, user_id=None):
    """Insert a tenant + user and return (tenant_id, user_id, raw_token)."""
    tid = tenant_id or str(uuid.uuid4())
    uid = user_id   or str(uuid.uuid4())

    # Ensure tenant exists
    db.execute(
        "INSERT OR IGNORE INTO tenants(id, name) VALUES (?, ?)",
        (tid, f"Tenant-{tid[:8]}"),
    )
    db.execute(
        "INSERT OR IGNORE INTO users(id, tenant_id, username, role, created_at) VALUES (?,?,?,?,?)",
        (uid, tid, f"user-{uid[:8]}", role, int(time.time())),
    )

    raw_token = generate_token()
    token_hash = hash_token(raw_token)
    db.execute(
        "INSERT INTO sessions(token_hash, user_id, tenant_id, expires_at) VALUES (?,?,?,?)",
        (token_hash, uid, tid, int(time.time()) + 3600),
    )
    db.commit()
    return tid, uid, raw_token


def _req(raw_token, body=None, query=None, raw_body=None, extra_headers=None):
    """Build a minimal request dict."""
    headers = {"Authorization": f"Bearer {raw_token}"}
    if extra_headers:
        headers.update(extra_headers)
    r = {"headers": headers, "body": body or {}, "query": query or {}}
    if raw_body is not None:
        r["raw_body"] = raw_body
    return r


@pytest.fixture()
def svc(db):
    return ReportService(db)


@pytest.fixture()
def viewer(db):
    return _make_user(db, role="viewer")


@pytest.fixture()
def editor(db):
    return _make_user(db, role="editor")


@pytest.fixture()
def admin(db):
    return _make_user(db, role="admin")
