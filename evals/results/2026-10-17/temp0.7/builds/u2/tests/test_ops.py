"""Tests for internal ops-console functions."""

import pytest

from reportkit.ops import purge_tenant, set_role
from reportkit.errors import NotFoundError, ValidationError
from reportkit.db import open_db, apply_schema
from reportkit.fixtures import make_tenant, make_user, make_report


@pytest.fixture()
def conn():
    db = open_db(":memory:")
    apply_schema(db)
    return db


def test_purge_tenant_removes_reports(conn):
    tid = make_tenant(conn, "PurgeCo")
    uid = make_user(conn, tid, role="editor")
    make_report(conn, uid, tid, "R1")
    make_report(conn, uid, tid, "R2")

    count = purge_tenant(conn, actor_id="ops", tenant_id=tid)
    assert count == 2

    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM reports WHERE tenant_id = ?", (tid,)
    ).fetchone()["n"]
    assert remaining == 0


def test_purge_tenant_not_found(conn):
    with pytest.raises(NotFoundError):
        purge_tenant(conn, actor_id="ops", tenant_id="ghost")


def test_purge_tenant_zero_reports(conn):
    tid = make_tenant(conn, "EmptyCo")
    count = purge_tenant(conn, actor_id="ops", tenant_id=tid)
    assert count == 0


def test_set_role_success(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")

    set_role(conn, actor_id="ops", user_id=uid, new_role="admin")

    row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "admin"


def test_set_role_invalid_role(conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    with pytest.raises(ValidationError):
        set_role(conn, actor_id="ops", user_id=uid, new_role="superuser")


def test_set_role_user_not_found(conn):
    with pytest.raises(NotFoundError):
        set_role(conn, actor_id="ops", user_id="ghost", new_role="editor")
