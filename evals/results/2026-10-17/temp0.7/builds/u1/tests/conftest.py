"""Shared pytest fixtures."""

import uuid
import pytest

from reportkit.db import init_schema, open_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token() -> str:
    return str(uuid.uuid4())


def seed_tenant(conn, *, tenant_id=None, suspended=0):
    tid = tenant_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, name, suspended) VALUES (?, ?, ?)",
        (tid, f"Tenant-{tid[:8]}", suspended),
    )
    conn.commit()
    return tid


def seed_user(conn, *, tenant_id, role="editor", user_id=None):
    uid = user_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
        (uid, tenant_id, f"user-{uid[:8]}", role),
    )
    conn.commit()
    return uid


def seed_session(conn, *, user_id, token=None, expires_offset="+1 hour"):
    tok = token or _make_token()
    conn.execute(
        """
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?))
        """,
        (tok, user_id, expires_offset),
    )
    conn.commit()
    return tok


def make_request(token, body=None, query=None, headers=None):
    h = {"Authorization": f"Bearer {token}"}
    if headers:
        h.update(headers)
    return {"headers": h, "body": body or {}, "query": query or {}}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn():
    c = open_db(":memory:")
    init_schema(c)
    return c


@pytest.fixture()
def tenant(conn):
    return seed_tenant(conn)


@pytest.fixture()
def editor(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="editor")
    tok = seed_session(conn, user_id=uid)
    return {"user_id": uid, "tenant_id": tenant, "token": tok}


@pytest.fixture()
def viewer(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="viewer")
    tok = seed_session(conn, user_id=uid)
    return {"user_id": uid, "tenant_id": tenant, "token": tok}


@pytest.fixture()
def admin(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="admin")
    tok = seed_session(conn, user_id=uid)
    return {"user_id": uid, "tenant_id": tenant, "token": tok}


@pytest.fixture()
def service(conn):
    from reportkit.service import ReportService
    from reportkit.events import EventRegistry
    return ReportService(conn, registry=EventRegistry())
