"""Tests for authentication and permission resolution."""
import pytest
from reportkit.auth import (
    resolve_caller,
    bearer_token,
    AuthError,
    PermissionError,
    permissions_for_role,
)
from reportkit.db import connect, apply_schema
from reportkit import fixtures as F


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


def test_permissions_viewer():
    p = permissions_for_role("viewer")
    assert "report:read" in p
    assert "report:write" not in p


def test_permissions_editor():
    p = permissions_for_role("editor")
    assert "report:read" in p
    assert "report:write" in p
    assert "report:delete" not in p


def test_permissions_admin():
    p = permissions_for_role("admin")
    assert p >= {"report:read", "report:write", "report:delete", "user:manage"}


def test_permissions_unknown_role():
    assert permissions_for_role("superuser") == frozenset()


def test_resolve_caller_valid(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="editor")
    token = F.make_session(conn, uid)
    caller = resolve_caller(conn, token)
    assert caller.user_id == uid
    assert caller.tenant_id == tid
    assert caller.role == "editor"
    assert caller.has("report:write")


def test_resolve_caller_expired(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid)
    token = F.make_session(conn, uid, ttl_seconds=-1)  # already expired
    with pytest.raises(AuthError):
        resolve_caller(conn, token)


def test_resolve_caller_bad_token(conn):
    with pytest.raises(AuthError):
        resolve_caller(conn, "not-a-real-token")


def test_resolve_caller_suspended_tenant(conn):
    tid = F.make_tenant(conn)
    conn.execute("UPDATE tenants SET suspended = 1 WHERE id = ?", (tid,))
    conn.commit()
    uid = F.make_user(conn, tid)
    token = F.make_session(conn, uid)
    with pytest.raises(AuthError, match="suspended"):
        resolve_caller(conn, token)


def test_bearer_token_extraction():
    request = {"headers": {"Authorization": "Bearer mytoken123"}}
    assert bearer_token(request) == "mytoken123"


def test_bearer_token_missing():
    with pytest.raises(AuthError):
        bearer_token({"headers": {}})


def test_caller_require_raises():
    tid = "t1"
    uid = "u1"
    from reportkit.auth import Caller
    caller = Caller(uid, tid, "viewer")
    with pytest.raises(PermissionError):
        caller.require("report:delete")
