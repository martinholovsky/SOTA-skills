"""Report CRUD and isolation tests."""

import uuid
import pytest

from tests.conftest import _make_user, _req
from reportkit.service import ReportService


def test_create_and_get_report(db, svc, editor):
    _, uid, raw = editor
    create = svc.create_report(_req(raw, body={"title": "My Report", "body": "Content"}))
    assert create["status"] == 200
    rid = create["body"]["report_id"]

    get = svc.get_report(_req(raw), rid)
    assert get["status"] == 200
    assert get["body"]["title"] == "My Report"
    assert get["body"]["body"] == "Content"


def test_get_nonexistent_returns_404(db, svc, viewer):
    _, _, raw = viewer
    resp = svc.get_report(_req(raw), str(uuid.uuid4()))
    assert resp["status"] == 404


def test_cross_tenant_isolation(db, svc):
    """User A cannot read User B's report even with a valid token."""
    tid_a, uid_a, raw_a = _make_user(db, role="editor")
    tid_b, uid_b, raw_b = _make_user(db, role="viewer")

    create = svc.create_report(_req(raw_a, body={"title": "Secret", "body": "data"}))
    rid = create["body"]["report_id"]

    # User B tries to get User A's report
    resp = svc.get_report(_req(raw_b), rid)
    assert resp["status"] == 404


def test_cross_user_same_tenant_isolation(db, svc):
    """Two users in the same tenant cannot read each other's reports."""
    tid = str(uuid.uuid4())
    _, uid_a, raw_a = _make_user(db, role="editor", tenant_id=tid)
    _, uid_b, raw_b = _make_user(db, role="viewer",  tenant_id=tid)

    create = svc.create_report(_req(raw_a, body={"title": "Mine", "body": "x"}))
    rid = create["body"]["report_id"]

    resp = svc.get_report(_req(raw_b), rid)
    assert resp["status"] == 404


def test_list_returns_only_own_reports(db, svc):
    tid = str(uuid.uuid4())
    _, _, raw_a = _make_user(db, role="editor", tenant_id=tid)
    _, _, raw_b = _make_user(db, role="editor", tenant_id=tid)

    svc.create_report(_req(raw_a, body={"title": "A1", "body": ""}))
    svc.create_report(_req(raw_a, body={"title": "A2", "body": ""}))
    svc.create_report(_req(raw_b, body={"title": "B1", "body": ""}))

    resp = svc.list_reports(_req(raw_a))
    assert resp["status"] == 200
    titles = {r["title"] for r in resp["body"]["reports"]}
    assert titles == {"A1", "A2"}
    assert "B1" not in titles


def test_list_newest_first(db, svc, editor):
    _, _, raw = editor
    svc.create_report(_req(raw, body={"title": "First", "body": ""}))
    svc.create_report(_req(raw, body={"title": "Second", "body": ""}))
    resp = svc.list_reports(_req(raw))
    assert resp["body"]["reports"][0]["title"] == "Second"


def test_delete_own_report(db, svc, admin):
    _, _, raw = admin
    create = svc.create_report(_req(raw, body={"title": "Bye", "body": ""}))
    rid = create["body"]["report_id"]
    del_resp = svc.delete_report(_req(raw), rid)
    assert del_resp["status"] == 200
    get_resp = svc.get_report(_req(raw), rid)
    assert get_resp["status"] == 404


def test_delete_other_users_report_returns_404(db, svc):
    tid = str(uuid.uuid4())
    _, _, raw_a = _make_user(db, role="admin", tenant_id=tid)
    _, _, raw_b = _make_user(db, role="admin", tenant_id=tid)

    create = svc.create_report(_req(raw_a, body={"title": "Mine", "body": ""}))
    rid = create["body"]["report_id"]

    resp = svc.delete_report(_req(raw_b), rid)
    assert resp["status"] == 404


def test_invalid_report_id_format(db, svc, viewer):
    _, _, raw = viewer
    resp = svc.get_report(_req(raw), "not-a-uuid")
    assert resp["status"] == 400
