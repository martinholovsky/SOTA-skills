"""Tests for create_report, get_report, list_reports, delete_report."""

import pytest

from reportkit.fixtures import make_report, bearer
from reportkit.errors import PermissionError


def test_create_report_success(svc, editor_token):
    req = {**bearer(editor_token), "body": {"title": "Q1 Summary", "body": "content"}}
    resp = svc.create_report(req)
    assert resp["status"] == 201
    assert resp["body"]["title"] == "Q1 Summary"
    assert "id" in resp["body"]


def test_create_report_viewer_forbidden(svc, viewer_token):
    req = {**bearer(viewer_token), "body": {"title": "Nope"}}
    resp = svc.create_report(req)
    assert resp["status"] == 403


def test_create_report_missing_title(svc, editor_token):
    req = {**bearer(editor_token), "body": {"title": "  "}}
    resp = svc.create_report(req)
    assert resp["status"] == 422


def test_create_report_no_auth(svc):
    req = {"headers": {}, "body": {"title": "X"}}
    resp = svc.create_report(req)
    assert resp["status"] == 401


def test_get_report_success(svc, conn, editor_token, tenant):
    uid = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (editor_token,)
    ).fetchone()["user_id"]
    rid = make_report(conn, uid, tenant, "My Report")

    resp = svc.get_report(bearer(editor_token), rid)
    assert resp["status"] == 200
    assert resp["body"]["id"] == rid
    assert resp["body"]["title"] == "My Report"


def test_get_report_wrong_tenant(svc, conn, editor_token):
    """A report from another tenant is not visible."""
    from reportkit.fixtures import make_tenant, make_user
    other_tenant = make_tenant(conn, "OtherCo")
    other_user   = make_user(conn, other_tenant, role="editor")
    rid = make_report(conn, other_user, other_tenant, "Secret")

    resp = svc.get_report(bearer(editor_token), rid)
    assert resp["status"] == 404


def test_get_report_not_found(svc, editor_token):
    resp = svc.get_report(bearer(editor_token), "no-such-id")
    assert resp["status"] == 404


def test_list_reports_empty(svc, editor_token):
    resp = svc.list_reports(bearer(editor_token))
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_list_reports_newest_first(svc, conn, editor_token, tenant):
    uid = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (editor_token,)
    ).fetchone()["user_id"]

    import time
    r1 = make_report(conn, uid, tenant, "First")
    time.sleep(0.01)
    r2 = make_report(conn, uid, tenant, "Second")

    resp = svc.list_reports(bearer(editor_token))
    ids = [r["id"] for r in resp["body"]["reports"]]
    assert ids.index(r2) < ids.index(r1)


def test_list_reports_only_own(svc, conn, editor_token, tenant):
    """Viewer's reports do not appear in editor's list."""
    from reportkit.fixtures import make_user, make_session
    other_uid = make_user(conn, tenant, role="viewer")
    make_report(conn, other_uid, tenant, "Other's report")

    resp = svc.list_reports(bearer(editor_token))
    assert resp["body"]["reports"] == []


def test_delete_report_admin(svc, conn, admin_token, tenant):
    uid = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (admin_token,)
    ).fetchone()["user_id"]
    rid = make_report(conn, uid, tenant, "To delete")

    resp = svc.delete_report(bearer(admin_token), rid)
    assert resp["status"] == 200
    assert resp["body"]["deleted"] is True

    # Confirm gone
    resp2 = svc.get_report(bearer(admin_token), rid)
    assert resp2["status"] == 404


def test_delete_report_editor_forbidden(svc, conn, editor_token, tenant):
    uid = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (editor_token,)
    ).fetchone()["user_id"]
    rid = make_report(conn, uid, tenant, "Protected")

    resp = svc.delete_report(bearer(editor_token), rid)
    assert resp["status"] == 403


def test_delete_report_not_found(svc, admin_token):
    resp = svc.delete_report(bearer(admin_token), "ghost-id")
    assert resp["status"] == 404
