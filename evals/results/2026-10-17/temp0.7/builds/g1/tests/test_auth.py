"""Authentication and session tests."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pytest

from reportkit.auth import AuthError, resolve_session, require_permission, ROLE_PERMISSIONS
from reportkit.validation import ValidationError, extract_bearer_token
from tests.conftest import _make_user, _make_session, make_request


def _hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


class TestSessionResolution:
    def test_valid_token_resolves(self, conn, tenant_id):
        uid = "11111111-1111-4111-8111-111111111111"
        _make_user(conn, tenant_id, role="editor", uid=uid)
        token = _make_session(conn, uid)
        p = resolve_session(conn, token)
        assert p.user_id == uid
        assert p.tenant_id == tenant_id
        assert "report:read" in p.permissions
        assert "report:write" in p.permissions

    def test_invalid_token_raises(self, conn):
        with pytest.raises(AuthError) as exc_info:
            resolve_session(conn, "a" * 32)
        assert exc_info.value.status == 401

    def test_expired_session_raises(self, conn, tenant_id):
        uid = "22222222-2222-4222-8222-222222222222"
        _make_user(conn, tenant_id, role="viewer", uid=uid)
        token = secrets.token_urlsafe(32)
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_hash(token), uid, past),
        )
        with pytest.raises(AuthError):
            resolve_session(conn, token)

    def test_missing_auth_header_raises(self):
        req = {"headers": {}, "body": {}, "query": {}}
        with pytest.raises(ValidationError):
            extract_bearer_token(req)

    def test_malformed_bearer_raises(self):
        req = {"headers": {"Authorization": "Basic abc"}, "body": {}, "query": {}}
        with pytest.raises(ValidationError):
            extract_bearer_token(req)


class TestPermissions:
    def test_viewer_permissions(self, conn, tenant_id):
        uid = "33333333-3333-4333-8333-333333333333"
        _make_user(conn, tenant_id, role="viewer", uid=uid)
        token = _make_session(conn, uid)
        p = resolve_session(conn, token)
        assert p.permissions == ROLE_PERMISSIONS["viewer"]
        assert "report:write" not in p.permissions

    def test_admin_has_all_permissions(self, conn, tenant_id):
        uid = "44444444-4444-4444-8444-444444444444"
        _make_user(conn, tenant_id, role="admin", uid=uid)
        token = _make_session(conn, uid)
        p = resolve_session(conn, token)
        for perm in ("report:read", "report:write", "report:delete", "user:manage"):
            assert perm in p.permissions

    def test_require_permission_denies(self, conn, viewer):
        token = viewer["token"]
        p = resolve_session(conn, token)
        with pytest.raises(AuthError) as exc_info:
            require_permission(p, "report:delete")
        assert exc_info.value.status == 403
