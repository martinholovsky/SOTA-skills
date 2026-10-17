"""Ops-console function tests."""

from __future__ import annotations

import uuid

import pytest

from reportkit.errors import BadRequest, NotFound
from reportkit.ops import purge_tenant, set_role
from tests.conftest import make_report, make_tenant, make_user


def test_purge_tenant_deletes_reports(conn):
    tid = make_tenant(conn)
    uid, _ = make_user(conn, tid, role="editor")
    make_report(conn, tid, uid, "R1")
    make_report(conn, tid, uid, "R2")
    actor = str(uuid.uuid4())

    deleted = purge_tenant(conn, actor, tid)
    assert deleted == 2

    remaining = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE tenant_id = ?", (tid,)
    ).fetchone()["c"]
    assert remaining == 0


def test_purge_tenant_only_affects_target(conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a, _ = make_user(conn, tid_a, role="editor")
    uid_b, _ = make_user(conn, tid_b, role="editor")
    make_report(conn, tid_a, uid_a, "A")
    make_report(conn, tid_b, uid_b, "B")
    actor = str(uuid.uuid4())

    purge_tenant(conn, actor, tid_a)

    count_b = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE tenant_id = ?", (tid_b,)
    ).fetchone()["c"]
    assert count_b == 1


def test_purge_tenant_invalid_uuid(conn):
    with pytest.raises(BadRequest):
        purge_tenant(conn, "not-uuid", "also-not-uuid")


def test_purge_tenant_not_found(conn):
    with pytest.raises(NotFound):
        purge_tenant(conn, str(uuid.uuid4()), str(uuid.uuid4()))


def test_set_role_changes_role(conn):
    tid = make_tenant(conn)
    uid, _ = make_user(conn, tid, role="viewer")
    actor = str(uuid.uuid4())

    set_role(conn, actor, tid, uid, "admin")

    row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "admin"


def test_set_role_invalid_role(conn):
    tid = make_tenant(conn)
    uid, _ = make_user(conn, tid, role="viewer")
    with pytest.raises(BadRequest):
        set_role(conn, str(uuid.uuid4()), tid, uid, "superuser")


def test_set_role_wrong_tenant(conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid, _ = make_user(conn, tid_a, role="viewer")
    with pytest.raises(NotFound):
        set_role(conn, str(uuid.uuid4()), tid_b, uid, "editor")


def test_set_role_invalid_uuid(conn):
    with pytest.raises(BadRequest):
        set_role(conn, "x", "y", "z", "editor")
