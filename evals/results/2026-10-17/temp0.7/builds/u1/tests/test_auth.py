"""Tests for authentication and authorisation helpers."""

import pytest

from reportkit.auth import AuthError, require_permission, resolve_caller
from tests.conftest import (
    make_request,
    seed_session,
    seed_tenant,
    seed_user,
)


def test_resolve_valid_token(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="editor")
    tok = seed_session(conn, user_id=uid)
    req = make_request(tok)
    caller = resolve_caller(conn, req)
    assert caller["user_id"] == uid
    assert caller["role"] == "editor"
    assert "report:read" in caller["permissions"]
    assert "report:write" in caller["permissions"]
    assert "report:delete" not in caller["permissions"]


def test_resolve_expired_token(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="viewer")
    tok = seed_session(conn, user_id=uid, expires_offset="-1 hour")
    with pytest.raises(AuthError) as exc_info:
        resolve_caller(conn, make_request(tok))
    assert exc_info.value.status == 401


def test_resolve_missing_token(conn):
    with pytest.raises(AuthError) as exc_info:
        resolve_caller(conn, {"headers": {}, "body": {}})
    assert exc_info.value.status == 401


def test_resolve_suspended_tenant(conn):
    tid = seed_tenant(conn, suspended=1)
    uid = seed_user(conn, tenant_id=tid, role="admin")
    tok = seed_session(conn, user_id=uid)
    with pytest.raises(AuthError) as exc_info:
        resolve_caller(conn, make_request(tok))
    assert exc_info.value.status == 403


def test_require_permission_ok(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="admin")
    tok = seed_session(conn, user_id=uid)
    caller = resolve_caller(conn, make_request(tok))
    # Should not raise
    require_permission(caller, "report:delete")
    require_permission(caller, "user:manage")


def test_require_permission_denied(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="viewer")
    tok = seed_session(conn, user_id=uid)
    caller = resolve_caller(conn, make_request(tok))
    with pytest.raises(AuthError) as exc_info:
        require_permission(caller, "report:write")
    assert exc_info.value.status == 403


def test_viewer_permissions(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="viewer")
    tok = seed_session(conn, user_id=uid)
    caller = resolve_caller(conn, make_request(tok))
    assert caller["permissions"] == frozenset({"report:read"})


def test_editor_permissions(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="editor")
    tok = seed_session(conn, user_id=uid)
    caller = resolve_caller(conn, make_request(tok))
    assert caller["permissions"] == frozenset({"report:read", "report:write"})


def test_admin_permissions(conn, tenant):
    uid = seed_user(conn, tenant_id=tenant, role="admin")
    tok = seed_session(conn, user_id=uid)
    caller = resolve_caller(conn, make_request(tok))
    assert caller["permissions"] == frozenset(
        {"report:read", "report:write", "report:delete", "user:manage"}
    )
