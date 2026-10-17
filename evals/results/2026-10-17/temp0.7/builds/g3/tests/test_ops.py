"""Tests for ops-console functions."""

import json
import pytest
from reportkit.ops import purge_tenant, set_role
from tests.conftest import make_tenant, make_user, make_report


def test_purge_tenant_deletes_reports(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid)
    make_report(conn, tid, uid, title="R1")
    make_report(conn, tid, uid, title="R2")

    count = purge_tenant(conn, actor_id="ops-admin", tenant_id=tid)
    assert count == 2

    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM reports WHERE tenant_id = ?", (tid,)
    ).fetchone()["n"]
    assert remaining == 0


def test_purge_tenant_writes_audit_log(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid)
    make_report(conn, tid, uid)

    purge_tenant(conn, actor_id="ops-admin", tenant_id=tid)

    row = conn.execute(
        "SELECT * FROM audit_log WHERE action = 'purge_tenant' AND target_id = ?",
        (tid,),
    ).fetchone()
    assert row is not None
    detail = json.loads(row["detail"])
    assert detail["reports_deleted"] == 1


def test_purge_tenant_does_not_affect_other_tenant(conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a)
    uid_b = make_user(conn, tid_b)
    make_report(conn, tid_a, uid_a)
    make_report(conn, tid_b, uid_b)

    purge_tenant(conn, actor_id="ops-admin", tenant_id=tid_a)

    remaining_b = conn.execute(
        "SELECT COUNT(*) AS n FROM reports WHERE tenant_id = ?", (tid_b,)
    ).fetchone()["n"]
    assert remaining_b == 1


def test_set_role_changes_role(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")

    set_role(conn, actor_id="ops-admin", target_user_id=uid, new_role="admin")

    row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "admin"


def test_set_role_writes_audit_log(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")

    set_role(conn, actor_id="ops-admin", target_user_id=uid, new_role="editor")

    row = conn.execute(
        "SELECT * FROM audit_log WHERE action = 'set_role' AND target_id = ?",
        (uid,),
    ).fetchone()
    assert row is not None
    detail = json.loads(row["detail"])
    assert detail["old_role"] == "viewer"
    assert detail["new_role"] == "editor"


def test_set_role_invalid_role(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid)
    with pytest.raises(ValueError, match="new_role"):
        set_role(conn, actor_id="ops-admin", target_user_id=uid, new_role="superuser")


def test_set_role_unknown_user(conn):
    with pytest.raises(ValueError, match="not found"):
        set_role(conn, actor_id="ops-admin", target_user_id="no-such-id", new_role="admin")


def test_purge_tenant_invalid_args(conn):
    with pytest.raises(ValueError):
        purge_tenant(conn, actor_id="", tenant_id="t1")
    with pytest.raises(ValueError):
        purge_tenant(conn, actor_id="a1", tenant_id="")
