"""Tests for authentication and authorisation helpers."""

import uuid
import pytest

from reportkit.auth import (
    resolve_caller,
    require_permission,
    permissions_for_role,
    AuthenticationError,
    AuthorizationError,
)
from reportkit.db import connect, apply_schema


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


def _make_session(conn, role="editor"):
    tenant_id = str(uuid.uuid4())
    user_id   = str(uuid.uuid4())
    token     = str(uuid.uuid4())
    conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tenant_id, "T"))
    conn.execute(
        "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
        (user_id, tenant_id, "u@example.com"),
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
    return token, user_id, tenant_id


def _req(token):
    return {"headers": {"Authorization": f"Bearer {token}"}}


class TestPermissionsForRole:
    def test_viewer(self):
        assert permissions_for_role("viewer") == {"report:read"}

    def test_editor(self):
        assert permissions_for_role("editor") == {"report:read", "report:write"}

    def test_admin(self):
        assert permissions_for_role("admin") >= {
            "report:read", "report:write", "report:delete", "user:manage"
        }

    def test_unknown_role_returns_empty(self):
        assert permissions_for_role("superuser") == frozenset()


class TestResolveCallerSuccess:
    def test_returns_caller_dict(self, conn):
        token, user_id, tenant_id = _make_session(conn, "editor")
        caller = resolve_caller(conn, _req(token))
        assert caller["user_id"]   == user_id
        assert caller["tenant_id"] == tenant_id
        assert caller["role"]      == "editor"
        assert "report:write" in caller["permissions"]

    def test_admin_has_all_permissions(self, conn):
        token, *_ = _make_session(conn, "admin")
        caller = resolve_caller(conn, _req(token))
        for perm in ("report:read", "report:write", "report:delete", "user:manage"):
            assert perm in caller["permissions"]


class TestResolveCallerFailures:
    def test_missing_header(self, conn):
        with pytest.raises(AuthenticationError):
            resolve_caller(conn, {"headers": {}})

    def test_bad_token(self, conn):
        with pytest.raises(AuthenticationError):
            resolve_caller(conn, _req("not-a-real-token"))

    def test_expired_session(self, conn):
        tenant_id = str(uuid.uuid4())
        user_id   = str(uuid.uuid4())
        token     = str(uuid.uuid4())
        conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tenant_id, "T"))
        conn.execute(
            "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
            (user_id, tenant_id, "x@example.com"),
        )
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at)
            VALUES (?, ?, '2000-01-01T00:00:00.000Z')
            """,
            (token, user_id),
        )
        conn.commit()
        with pytest.raises(AuthenticationError):
            resolve_caller(conn, _req(token))

    def test_suspended_tenant(self, conn):
        token, _, tenant_id = _make_session(conn, "editor")
        conn.execute(
            "UPDATE tenants SET suspended = 1 WHERE id = ?", (tenant_id,)
        )
        conn.commit()
        with pytest.raises(AuthorizationError, match="suspended"):
            resolve_caller(conn, _req(token))


class TestRequirePermission:
    def test_passes_when_held(self):
        caller = {"permissions": frozenset({"report:read"})}
        require_permission(caller, "report:read")  # no exception

    def test_raises_when_missing(self):
        caller = {"permissions": frozenset({"report:read"})}
        with pytest.raises(AuthorizationError):
            require_permission(caller, "report:delete")
