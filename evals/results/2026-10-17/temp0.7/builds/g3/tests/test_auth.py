"""Tests for authentication and session resolution."""

import hashlib
import uuid
import pytest

from reportkit.auth import AuthError, resolve_principal
from tests.conftest import make_tenant, make_user, make_session, auth_header


def test_valid_token_resolves(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    principal = resolve_principal({"headers": auth_header(token)}, conn)
    assert principal.user_id   == uid
    assert principal.tenant_id == tid
    assert principal.role      == "editor"
    assert "report:read"  in principal.permissions
    assert "report:write" in principal.permissions
    assert "report:delete" not in principal.permissions


def test_missing_header_raises(conn):
    with pytest.raises(AuthError) as exc_info:
        resolve_principal({"headers": {}}, conn)
    assert exc_info.value.status == 401


def test_empty_bearer_raises(conn):
    with pytest.raises(AuthError):
        resolve_principal({"headers": {"Authorization": "Bearer "}}, conn)


def test_expired_session_raises(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid)
    token = make_session(conn, uid, expires_offset="-1 second")

    with pytest.raises(AuthError) as exc_info:
        resolve_principal({"headers": auth_header(token)}, conn)
    assert exc_info.value.status == 401


def test_suspended_tenant_raises(conn):
    tid = make_tenant(conn, suspended=1)
    uid = make_user(conn, tid)
    token = make_session(conn, uid)

    with pytest.raises(AuthError) as exc_info:
        resolve_principal({"headers": auth_header(token)}, conn)
    assert exc_info.value.status == 401


def test_unknown_token_raises(conn):
    with pytest.raises(AuthError):
        resolve_principal({"headers": {"Authorization": "Bearer notarealtoken"}}, conn)


def test_viewer_lacks_write(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    principal = resolve_principal({"headers": auth_header(token)}, conn)
    with pytest.raises(AuthError) as exc_info:
        principal.require("report:write")
    assert exc_info.value.status == 403


def test_admin_has_all_permissions(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)
    principal = resolve_principal({"headers": auth_header(token)}, conn)
    for perm in ("report:read", "report:write", "report:delete", "user:manage"):
        assert principal.has(perm)
