"""Authentication and authorisation unit tests."""

import pytest
from tests.conftest import (
    make_request, seed_tenant, seed_user, seed_session, make_token
)
from reportkit.auth import (
    authenticate, require_permission, AuthError, permissions_for_role
)


def test_valid_token_returns_user(conn, tenant_id):
    uid = seed_user(conn, tenant_id, role="editor")
    token = seed_session(conn, uid)
    user = authenticate(conn, make_request(token))
    assert user["user_id"] == uid
    assert user["role"] == "editor"


def test_expired_token_raises(conn, tenant_id):
    uid = seed_user(conn, tenant_id)
    token = seed_session(conn, uid, expires_offset="-1 day")
    with pytest.raises(AuthError) as exc_info:
        authenticate(conn, make_request(token))
    assert exc_info.value.status == 401


def test_unknown_token_raises(conn):
    with pytest.raises(AuthError) as exc_info:
        authenticate(conn, make_request(make_token()))
    assert exc_info.value.status == 401


def test_missing_auth_header_raises(conn):
    with pytest.raises(AuthError) as exc_info:
        authenticate(conn, {"headers": {}, "body": {}})
    assert exc_info.value.status == 401


def test_suspended_tenant_raises(conn):
    tid = seed_tenant(conn, name="Suspended Corp")
    conn.execute("UPDATE tenants SET suspended = 1 WHERE id = ?", (tid,))
    conn.commit()
    uid = seed_user(conn, tid)
    token = seed_session(conn, uid)
    with pytest.raises(AuthError) as exc_info:
        authenticate(conn, make_request(token))
    assert exc_info.value.status == 403


def test_viewer_permissions():
    perms = permissions_for_role("viewer")
    assert "report:read" in perms
    assert "report:write" not in perms
    assert "report:delete" not in perms
    assert "user:manage" not in perms


def test_editor_permissions():
    perms = permissions_for_role("editor")
    assert "report:read" in perms
    assert "report:write" in perms
    assert "report:delete" not in perms


def test_admin_permissions():
    perms = permissions_for_role("admin")
    assert perms >= {"report:read", "report:write", "report:delete", "user:manage"}


def test_require_permission_raises_for_insufficient_role(conn, tenant_id):
    uid = seed_user(conn, tenant_id, role="viewer")
    token = seed_session(conn, uid)
    user = authenticate(conn, make_request(token))
    with pytest.raises(AuthError) as exc_info:
        require_permission(user, "report:write")
    assert exc_info.value.status == 403
