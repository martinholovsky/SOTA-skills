"""Authentication and session resolution tests."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from reportkit.auth import resolve_principal
from reportkit.errors import TenantSuspended, Unauthorized
from tests.conftest import _hash_token, _iso, make_tenant, make_user


def test_valid_token_resolves(conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="editor")
    principal = resolve_principal(conn, {"headers": {"Authorization": f"Bearer {token}"}})
    assert principal["user_id"] == uid
    assert principal["tenant_id"] == tid
    assert principal["role"] == "editor"
    assert "report:read" in principal["permissions"]
    assert "report:write" in principal["permissions"]
    assert "report:delete" not in principal["permissions"]


def test_missing_header_raises(conn):
    with pytest.raises(Unauthorized):
        resolve_principal(conn, {"headers": {}})


def test_wrong_token_raises(conn):
    tid = make_tenant(conn)
    make_user(conn, tid)
    with pytest.raises(Unauthorized):
        resolve_principal(conn, {"headers": {"Authorization": "Bearer wrong_token"}})


def test_expired_token_raises(conn):
    tid = make_tenant(conn)
    uid = str(uuid.uuid4())
    conn.execute("INSERT INTO users (id, tenant_id, role) VALUES (?, ?, ?)", (uid, tid, "viewer"))
    token = "expired_tok"
    past = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), uid, past),
    )
    with pytest.raises(Unauthorized):
        resolve_principal(conn, {"headers": {"Authorization": f"Bearer {token}"}})


def test_suspended_tenant_raises(conn):
    tid = make_tenant(conn, suspended=True)
    _, token = make_user(conn, tid)
    with pytest.raises(TenantSuspended):
        resolve_principal(conn, {"headers": {"Authorization": f"Bearer {token}"}})


def test_role_permissions_viewer(conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    p = resolve_principal(conn, {"headers": {"Authorization": f"Bearer {token}"}})
    assert p["permissions"] == frozenset({"report:read"})


def test_role_permissions_admin(conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="admin")
    p = resolve_principal(conn, {"headers": {"Authorization": f"Bearer {token}"}})
    assert "user:manage" in p["permissions"]
    assert "report:delete" in p["permissions"]
