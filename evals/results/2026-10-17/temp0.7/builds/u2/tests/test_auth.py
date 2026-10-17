"""Authentication and permission tests."""

import pytest

from reportkit.auth import resolve_caller, require_permission
from reportkit.errors import AuthenticationError, PermissionError
from reportkit.db import open_db, apply_schema
from reportkit.fixtures import make_tenant, make_user, make_session


@pytest.fixture()
def conn():
    db = open_db(":memory:")
    apply_schema(db)
    return db


def test_resolve_caller_success(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    caller = resolve_caller(conn, token)
    assert caller["user_id"] == uid
    assert caller["tenant_id"] == tid
    assert caller["role"] == "editor"
    assert "report:read" in caller["permissions"]
    assert "report:write" in caller["permissions"]
    assert "report:delete" not in caller["permissions"]


def test_resolve_caller_bad_token(conn):
    with pytest.raises(AuthenticationError):
        resolve_caller(conn, "not-a-real-token")


def test_resolve_caller_empty_token(conn):
    with pytest.raises(AuthenticationError):
        resolve_caller(conn, "")


def test_resolve_caller_expired(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    # Insert an already-expired session
    token = "expired-token"
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, uid, "2000-01-01T00:00:00.000Z"),
    )
    conn.commit()
    with pytest.raises(AuthenticationError, match="expired"):
        resolve_caller(conn, token)


def test_resolve_caller_suspended_tenant(conn):
    tid = make_tenant(conn)
    conn.execute("UPDATE tenants SET suspended = 1 WHERE id = ?", (tid,))
    conn.commit()
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)
    with pytest.raises(AuthenticationError, match="suspended"):
        resolve_caller(conn, token)


def test_viewer_permissions(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    caller = resolve_caller(conn, token)
    assert caller["permissions"] == frozenset({"report:read"})


def test_admin_permissions(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)
    caller = resolve_caller(conn, token)
    assert {"report:read", "report:write", "report:delete", "user:manage"}.issubset(
        caller["permissions"]
    )


def test_require_permission_ok(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    caller = resolve_caller(conn, token)
    # Should not raise
    require_permission(caller, "report:read")
    require_permission(caller, "report:write")


def test_require_permission_denied(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    caller = resolve_caller(conn, token)
    with pytest.raises(PermissionError):
        require_permission(caller, "report:delete")
