"""Shared pytest fixtures."""

import uuid
import pytest

from reportkit.db import connect, init_schema
from reportkit.service import ReportService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_token() -> str:
    return str(uuid.uuid4())


def seed_tenant(conn, tenant_id=None, name="Acme"):
    tid = tenant_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, name) VALUES (?, ?)", (tid, name)
    )
    conn.commit()
    return tid


def seed_user(conn, tenant_id, role="editor", username=None):
    uid = str(uuid.uuid4())
    uname = username or f"user_{uid[:8]}"
    conn.execute(
        "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
        (uid, tenant_id, uname, role),
    )
    conn.commit()
    return uid


def seed_session(conn, user_id, expires_offset="+1 day"):
    token = make_token()
    conn.execute(
        """
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?))
        """,
        (token, user_id, expires_offset),
    )
    conn.commit()
    return token


def make_request(token, body=None, query=None):
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body": body or {},
        "query": query or {},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn():
    c = connect(":memory:")
    init_schema(c)
    return c


@pytest.fixture()
def svc(conn):
    return ReportService(conn=conn)


@pytest.fixture()
def tenant_id(conn):
    return seed_tenant(conn)


@pytest.fixture()
def editor_token(conn, tenant_id):
    uid = seed_user(conn, tenant_id, role="editor")
    return seed_session(conn, uid)


@pytest.fixture()
def viewer_token(conn, tenant_id):
    uid = seed_user(conn, tenant_id, role="viewer")
    return seed_session(conn, uid)


@pytest.fixture()
def admin_token(conn, tenant_id):
    uid = seed_user(conn, tenant_id, role="admin")
    return seed_session(conn, uid)
