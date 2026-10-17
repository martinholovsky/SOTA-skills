"""Tests for the report CRUD endpoints."""
import pytest
from tests.conftest import req


def test_create_report_editor(svc, editor):
    uid, token = editor
    resp = svc.create_report(req(token, body={"title": "My Report", "body": "content"}))
    assert resp["status"] == 201
    assert resp["report"]["title"] == "My Report"
    assert resp["report"]["owner_id"] == uid


def test_create_report_viewer_forbidden(svc, viewer):
    _, token = viewer
    resp = svc.create_report(req(token, body={"title": "Nope"}))
    # viewer lacks report:write; service raises PermissionError which propagates
    # (callers / adapters handle it).  We test the exception path here.
    from reportkit.auth import PermissionError
    with pytest.raises(PermissionError):
        svc.create_report(req(token, body={"title": "Nope"}))


def test_create_report_missing_title(svc, editor):
    _, token = editor
    resp = svc.create_report(req(token, body={}))
    assert resp["status"] == 400


def test_get_report(svc, conn, tenant, editor):
    uid, token = editor
    from reportkit import fixtures as F
    rid = F.make_report(conn, tenant, uid, title="Hello")
    resp = svc.get_report(req(token), rid)
    assert resp["status"] == 200
    assert resp["report"]["id"] == rid


def test_get_report_not_found(svc, editor):
    _, token = editor
    resp = svc.get_report(req(token), "00000000-0000-0000-0000-000000000000")
    assert resp["status"] == 404


def test_get_report_wrong_tenant(svc, conn, editor):
    _, token = editor
    # Create a report in a different tenant
    other_tid = __import__("reportkit.fixtures", fromlist=["make_tenant"]).make_tenant(conn, "Other")
    other_uid = __import__("reportkit.fixtures", fromlist=["make_user"]).make_user(conn, other_tid)
    from reportkit import fixtures as F
    rid = F.make_report(conn, other_tid, other_uid, title="Secret")
    resp = svc.get_report(req(token), rid)
    assert resp["status"] == 404


def test_list_reports(svc, conn, tenant, editor):
    uid, token = editor
    from reportkit import fixtures as F
    F.make_report(conn, tenant, uid, title="A")
    F.make_report(conn, tenant, uid, title="B")
    resp = svc.list_reports(req(token))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 2


def test_list_reports_newest_first(svc, conn, tenant, editor):
    import time
    uid, token = editor
    from reportkit import fixtures as F
    r1 = F.make_report(conn, tenant, uid, title="First")
    time.sleep(0.01)
    r2 = F.make_report(conn, tenant, uid, title="Second")
    resp = svc.list_reports(req(token))
    ids = [r["id"] for r in resp["reports"]]
    assert ids[0] == r2  # newest first


def test_list_reports_only_own(svc, conn, tenant, editor):
    """Reports owned by another user in the same tenant are not listed."""
    uid, token = editor
    other_uid = __import__("reportkit.fixtures", fromlist=["make_user"]).make_user(conn, tenant, role="editor")
    from reportkit import fixtures as F
    F.make_report(conn, tenant, other_uid, title="Other's")
    F.make_report(conn, tenant, uid, title="Mine")
    resp = svc.list_reports(req(token))
    assert len(resp["reports"]) == 1
    assert resp["reports"][0]["title"] == "Mine"


def test_delete_report_admin(svc, conn, tenant, admin):
    uid, token = admin
    from reportkit import fixtures as F
    rid = F.make_report(conn, tenant, uid, title="To Delete")
    resp = svc.delete_report(req(token), rid)
    assert resp["status"] == 200
    assert resp["deleted"] == rid
    # Confirm gone
    resp2 = svc.get_report(req(token), rid)
    assert resp2["status"] == 404


def test_delete_report_editor_forbidden(svc, conn, tenant, editor):
    uid, token = editor
    from reportkit import fixtures as F
    rid = F.make_report(conn, tenant, uid, title="Mine")
    from reportkit.auth import PermissionError
    with pytest.raises(PermissionError):
        svc.delete_report(req(token), rid)


def test_delete_report_not_found(svc, admin):
    _, token = admin
    resp = svc.delete_report(req(token), "00000000-0000-0000-0000-000000000000")
    assert resp["status"] == 404
