"""
Tests for authentication and session resolution.
"""

import datetime
import hashlib
import uuid

import pytest

from reportkit.auth import resolve_principal, hash_token
from reportkit.errors import Unauthorized, TenantSuspended
from tests.conftest import make_user


def _uuid():
    return str(uuid.uuid4())


class TestResolveSession:
    def test_valid_token_returns_principal(self, db, tenant_a):
        user_id, token = make_user(db, tenant_a, "editor")
        p = resolve_principal(db, token)
        assert p.user_id == user_id
        assert p.tenant_id == tenant_a
        assert p.role == "editor"

    def test_missing_token_raises(self, db):
        with pytest.raises(Unauthorized):
            resolve_principal(db, "")

    def test_none_token_raises(self, db):
        with pytest.raises(Unauthorized):
            resolve_principal(db, None)  # type: ignore[arg-type]

    def test_unknown_token_raises(self, db):
        with pytest.raises(Unauthorized):
            resolve_principal(db, _uuid())

    def test_expired_token_raises(self, db, tenant_a):
        user_id = _uuid()
        token = _uuid()
        token_hash = hash_token(token)
        past = "2000-01-01T00:00:00.000000Z"
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'viewer')",
            (user_id, tenant_a),
        )
        db.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, past),
        )
        db.commit()
        with pytest.raises(Unauthorized):
            resolve_principal(db, token)

    def test_suspended_tenant_raises(self, db, tenant_a):
        user_id, token = make_user(db, tenant_a, "viewer")
        db.execute(
            "UPDATE tenants SET suspended = 1 WHERE id = ?", (tenant_a,)
        )
        db.commit()
        with pytest.raises(TenantSuspended):
            resolve_principal(db, token)

    def test_oversized_token_raises(self, db):
        with pytest.raises(Unauthorized):
            resolve_principal(db, "x" * 513)


class TestPermissions:
    def test_viewer_permissions(self, db, tenant_a):
        _, token = make_user(db, tenant_a, "viewer")
        p = resolve_principal(db, token)
        assert "report:read" in p.permissions
        assert "report:write" not in p.permissions
        assert "report:delete" not in p.permissions
        assert "user:manage" not in p.permissions

    def test_editor_permissions(self, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        p = resolve_principal(db, token)
        assert "report:read" in p.permissions
        assert "report:write" in p.permissions
        assert "report:delete" not in p.permissions

    def test_admin_permissions(self, db, tenant_a):
        _, token = make_user(db, tenant_a, "admin")
        p = resolve_principal(db, token)
        assert "report:delete" in p.permissions
        assert "user:manage" in p.permissions

    def test_require_raises_on_missing_permission(self, db, tenant_a):
        from reportkit.errors import Forbidden
        _, token = make_user(db, tenant_a, "viewer")
        p = resolve_principal(db, token)
        with pytest.raises(Forbidden):
            p.require("report:write")
