"""Tests for authentication and authorisation helpers."""

import pytest

from reportkit.auth import (
    extract_token,
    permissions_for_role,
    require_permission,
    resolve_caller,
)
from reportkit.errors import AuthenticationError, AuthorisationError
from reportkit.fixtures import build_fixture_db
from reportkit.ids import new_id
from reportkit.db import apply_schema, open_db


# ---------------------------------------------------------------------------
# permissions_for_role
# ---------------------------------------------------------------------------

class TestPermissionsForRole:
    def test_viewer_has_read_only(self):
        perms = permissions_for_role("viewer")
        assert "report:read" in perms
        assert "report:write" not in perms
        assert "report:delete" not in perms
        assert "user:manage" not in perms

    def test_editor_has_read_and_write(self):
        perms = permissions_for_role("editor")
        assert {"report:read", "report:write"} <= perms
        assert "report:delete" not in perms

    def test_admin_has_all(self):
        perms = permissions_for_role("admin")
        assert {"report:read", "report:write", "report:delete", "user:manage"} <= perms

    def test_unknown_role_returns_empty(self):
        assert permissions_for_role("superuser") == frozenset()


# ---------------------------------------------------------------------------
# extract_token
# ---------------------------------------------------------------------------

class TestExtractToken:
    def test_extracts_bearer(self):
        req = {"headers": {"Authorization": "Bearer abc123"}}
        assert extract_token(req) == "abc123"

    def test_case_insensitive_scheme(self):
        req = {"headers": {"Authorization": "bearer xyz"}}
        assert extract_token(req) == "xyz"

    def test_missing_header_returns_empty(self):
        assert extract_token({}) == ""
        assert extract_token({"headers": {}}) == ""

    def test_non_bearer_returns_empty(self):
        req = {"headers": {"Authorization": "Basic dXNlcjpwYXNz"}}
        assert extract_token(req) == ""


# ---------------------------------------------------------------------------
# resolve_caller
# ---------------------------------------------------------------------------

class TestResolveCaller:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()

    def test_valid_token_returns_caller(self):
        token = self.ctx["tokens"]["editor"]
        caller = resolve_caller(self.conn, token)
        assert caller["user_id"] == self.ctx["users"]["editor"]
        assert caller["tenant_id"] == self.ctx["tenant_id"]
        assert caller["role"] == "editor"
        assert "report:write" in caller["permissions"]

    def test_empty_token_raises(self):
        with pytest.raises(AuthenticationError):
            resolve_caller(self.conn, "")

    def test_unknown_token_raises(self):
        with pytest.raises(AuthenticationError):
            resolve_caller(self.conn, "not-a-real-token")

    def test_expired_token_raises(self):
        conn = open_db(":memory:")
        apply_schema(conn)
        tid = new_id()
        uid = new_id()
        conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tid, "T"))
        conn.execute(
            "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
            (uid, tid, "u", "viewer"),
        )
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            ("expired-tok", uid, "2000-01-01T00:00:00.000Z"),
        )
        conn.commit()
        with pytest.raises(AuthenticationError):
            resolve_caller(conn, "expired-tok")

    def test_suspended_tenant_raises(self):
        conn, ctx = build_fixture_db()
        conn.execute(
            "UPDATE tenants SET suspended = 1 WHERE id = ?",
            (ctx["tenant_id"],),
        )
        conn.commit()
        with pytest.raises(AuthorisationError, match="suspended"):
            resolve_caller(conn, ctx["tokens"]["admin"])


# ---------------------------------------------------------------------------
# require_permission
# ---------------------------------------------------------------------------

class TestRequirePermission:
    def test_passes_when_permitted(self):
        caller = {"permissions": frozenset({"report:read"})}
        require_permission(caller, "report:read")  # no exception

    def test_raises_when_not_permitted(self):
        caller = {"permissions": frozenset({"report:read"})}
        with pytest.raises(AuthorisationError):
            require_permission(caller, "report:delete")
