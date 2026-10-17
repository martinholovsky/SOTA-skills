"""Ops console tests."""

import pytest
from tests.conftest import seed_tenant, seed_user, seed_session, make_request
from reportkit.ops import purge_tenant, set_role
from reportkit.auth import AuthError


def test_purge_tenant_removes_reports(svc, conn):
    tid = seed_tenant(conn, name="Doomed Corp")
    uid = seed_user(conn, tid, role="editor")
    tok = seed_session(conn, uid)

    for i in range(4):
        svc.create_report(make_request(tok, body={"title": f"Report {i}"}))

    # Admin actor in a different tenant performs the purge
    admin_tid = seed_tenant(conn, name="Ops Tenant")
    admin_uid = seed_user(conn, admin_tid, role="admin")

    result = purge_tenant(conn, admin_uid, tid)
    assert result["deleted_reports"] == 4

    # Verify reports are gone
    rows = conn.execute(
        "SELECT id FROM reports WHERE tenant_id = ?", (tid,)
    ).fetchall()
    assert len(rows) == 0


def test_purge_tenant_non_admin_forbidden(conn):
    tid = seed_tenant(conn)
    editor_uid = seed_user(conn, tid, role="editor")

    with pytest.raises(AuthError) as exc_info:
        purge_tenant(conn, editor_uid, tid)
    assert exc_info.value.status == 403


def test_purge_tenant_unknown_actor(conn):
    tid = seed_tenant(conn)
    with pytest.raises(AuthError):
        purge_tenant(conn, "ghost-actor", tid)


def test_set_role_success(conn):
    tid = seed_tenant(conn)
    admin_uid = seed_user(conn, tid, role="admin")
    target_uid = seed_user(conn, tid, role="viewer")

    result = set_role(conn, admin_uid, target_uid, "editor")
    assert result["new_role"] == "editor"

    row = conn.execute("SELECT role FROM users WHERE id = ?", (target_uid,)).fetchone()
    assert row["role"] == "editor"


def test_set_role_non_admin_forbidden(conn):
    tid = seed_tenant(conn)
    editor_uid = seed_user(conn, tid, role="editor")
    target_uid = seed_user(conn, tid, role="viewer")

    with pytest.raises(AuthError) as exc_info:
        set_role(conn, editor_uid, target_uid, "admin")
    assert exc_info.value.status == 403


def test_set_role_invalid_role(conn):
    tid = seed_tenant(conn)
    admin_uid = seed_user(conn, tid, role="admin")
    target_uid = seed_user(conn, tid, role="viewer")

    with pytest.raises(ValueError, match="Invalid role"):
        set_role(conn, admin_uid, target_uid, "superuser")


def test_set_role_unknown_target(conn):
    tid = seed_tenant(conn)
    admin_uid = seed_user(conn, tid, role="admin")

    with pytest.raises(ValueError, match="not found"):
        set_role(conn, admin_uid, "ghost-user", "editor")
