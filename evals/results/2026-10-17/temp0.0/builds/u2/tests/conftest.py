"""Shared pytest fixtures."""

import uuid
import pytest

from reportkit.db import connect, apply_schema
from reportkit.handlers import ReportHandlers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(conn, *, role="editor"):
    """
    Insert a tenant, user, role, and session; return a dict with all IDs and
    the bearer token so tests can build request dicts easily.
    """
    tenant_id = str(uuid.uuid4())
    user_id   = str(uuid.uuid4())
    token     = str(uuid.uuid4())

    conn.execute(
        "INSERT INTO tenants (id, name) VALUES (?, ?)",
        (tenant_id, "Acme Corp"),
    )
    conn.execute(
        "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
        (user_id, tenant_id, "alice@example.com"),
    )
    conn.execute(
        "INSERT INTO roles (user_id, tenant_id, role) VALUES (?, ?, ?)",
        (user_id, tenant_id, role),
    )
    conn.execute(
        """
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+1 hour'))
        """,
        (token, user_id),
    )
    conn.commit()
    return {"tenant_id": tenant_id, "user_id": user_id, "token": token}


def _request(token: str, body=None, query=None) -> dict:
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body":    body or {},
        "query":   query or {},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


@pytest.fixture()
def editor_ctx(conn):
    return conn, _seed(conn, role="editor"), ReportHandlers(conn)


@pytest.fixture()
def viewer_ctx(conn):
    return conn, _seed(conn, role="viewer"), ReportHandlers(conn)


@pytest.fixture()
def admin_ctx(conn):
    return conn, _seed(conn, role="admin"), ReportHandlers(conn)
