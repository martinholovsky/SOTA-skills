"""Tests for ops-console operations."""
import pytest
from reportkit.db import connect, apply_schema
from reportkit.ops import purge_tenant, set_role
from reportkit.auth import PermissionError
from reportkit import fixtures as F


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


def test_purge_tenant_trusted_caller(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="editor")
    F.make_report(conn, tid, uid, title="R1")
    F.make_report(conn, tid, uid, title="R2")
    count = purge_tenant(conn, actor_id=None, tenant_id=tid)
    assert count == 2
    remaining = conn.execute("SELECT COUNT(*) FROM reports WHERE tenant_id = ?", (tid,)).fetchone()[0]
    assert remaining == 0


def test_purge_tenant_admin_actor(conn):
    tid = F.make_tenant(conn)
    admin_id = F.make_user(conn, tid, role="admin")
    uid = F.make_user(conn, tid, role="viewer")
    F.make_report(conn, tid, uid, title="R")
    count = purge_tenant(conn, actor_id=admin_id, tenant_id=tid)
    assert count == 1


def test_purge_tenant_non_admin_forbidden(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="editor")
    with pytest.raises(PermissionError):
        purge_tenant(conn, actor_id=uid, tenant_id=tid)


def test_set_role_trusted(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="viewer")
    set_role(conn, actor_id=None, tenant_id=tid, target_user_id=uid, new_role="admin")
    row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "admin"


def test_set_role_admin_actor(conn):
    tid = F.make_tenant(conn)
    admin_id = F.make_user(conn, tid, role="admin")
    uid = F.make_user(conn, tid, role="viewer")
    set_role(conn, actor_id=admin_id, tenant_id=tid, target_user_id=uid, new_role="editor")
    row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "editor"


def test_set_role_non_admin_forbidden(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="editor")
    with pytest.raises(PermissionError):
        set_role(conn, actor_id=uid, tenant_id=tid, target_user_id=uid, new_role="admin")


def test_set_role_invalid_role(conn):
    tid = F.make_tenant(conn)
    uid = F.make_user(conn, tid, role="viewer")
    with pytest.raises(ValueError):
        set_role(conn, actor_id=None, tenant_id=tid, target_user_id=uid, new_role="superuser")


def test_set_role_user_not_found(conn):
    tid = F.make_tenant(conn)
    with pytest.raises(ValueError):
        set_role(conn, actor_id=None, tenant_id=tid,
                 target_user_id="00000000-0000-0000-0000-000000000000",
                 new_role="editor")
