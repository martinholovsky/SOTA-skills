"""Ops-console function tests."""

import uuid
import pytest

from tests.conftest import _make_user, _req
from reportkit.ops import purge_tenant, set_role
from reportkit.service import ReportService


def test_purge_tenant_deletes_reports(db, svc):
    tid = str(uuid.uuid4())
    actor_id = str(uuid.uuid4())
    _, _, raw = _make_user(db, role="editor", tenant_id=tid)

    svc.create_report(_req(raw, body={"title": "R1", "body": ""}))
    svc.create_report(_req(raw, body={"title": "R2", "body": ""}))

    count = purge_tenant(db, actor_id, tid)
    assert count == 2

    # Verify reports are gone
    rows = db.execute("SELECT id FROM reports WHERE tenant_id=?", (tid,)).fetchall()
    assert rows == []


def test_purge_tenant_writes_audit_log(db, svc):
    tid = str(uuid.uuid4())
    actor_id = str(uuid.uuid4())
    _, _, raw = _make_user(db, role="editor", tenant_id=tid)
    svc.create_report(_req(raw, body={"title": "X", "body": ""}))

    purge_tenant(db, actor_id, tid)

    row = db.execute(
        "SELECT * FROM audit_log WHERE action='ops.tenant_purged' AND tenant_id=?",
        (tid,),
    ).fetchone()
    assert row is not None
    assert row["actor_id"] == actor_id


def test_set_role_changes_role(db):
    actor_id = str(uuid.uuid4())
    tid, uid, raw = _make_user(db, role="viewer")

    set_role(db, actor_id, tid, uid, "editor")

    row = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    assert row["role"] == "editor"


def test_set_role_invalidates_permission_cache(db, svc):
    actor_id = str(uuid.uuid4())
    tid, uid, raw = _make_user(db, role="viewer")

    # Warm the cache by making a request
    svc.list_reports(_req(raw))

    cache_before = db.execute(
        "SELECT * FROM permission_cache WHERE user_id=?", (uid,)
    ).fetchone()
    assert cache_before is not None

    set_role(db, actor_id, tid, uid, "editor")

    cache_after = db.execute(
        "SELECT * FROM permission_cache WHERE user_id=?", (uid,)
    ).fetchone()
    assert cache_after is None


def test_set_role_nonexistent_user_raises(db):
    actor_id = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    uid = str(uuid.uuid4())
    with pytest.raises(ValueError, match="not found"):
        set_role(db, actor_id, tid, uid, "admin")


def test_set_role_invalid_role_raises(db):
    actor_id = str(uuid.uuid4())
    tid, uid, _ = _make_user(db, role="viewer")
    with pytest.raises(Exception):
        set_role(db, actor_id, tid, uid, "superuser")


def test_purge_tenant_invalid_uuid_raises(db):
    with pytest.raises(Exception):
        purge_tenant(db, "not-a-uuid", str(uuid.uuid4()))


def test_set_role_writes_audit_log(db):
    actor_id = str(uuid.uuid4())
    tid, uid, _ = _make_user(db, role="viewer")
    set_role(db, actor_id, tid, uid, "admin")

    row = db.execute(
        "SELECT * FROM audit_log WHERE action='ops.role_changed' AND target_id=?",
        (uid,),
    ).fetchone()
    assert row is not None
    assert row["actor_id"] == actor_id
