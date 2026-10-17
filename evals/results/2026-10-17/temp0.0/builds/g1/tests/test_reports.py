"""Report CRUD tests — including multi-tenant isolation and IDOR checks."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers, make_report, make_tenant, make_user


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------


def test_create_report_success(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="editor")
    resp = svc.create_report(
        {"headers": auth_headers(token), "body": {"title": "Q1 Report", "body": "content"}}
    )
    assert resp["status"] == 201
    assert resp["body"]["title"] == "Q1 Report"
    assert "id" in resp["body"]


def test_create_report_viewer_forbidden(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.create_report(
        {"headers": auth_headers(token), "body": {"title": "X"}}
    )
    assert resp["status"] == 403


def test_create_report_missing_title(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.create_report({"headers": auth_headers(token), "body": {}})
    assert resp["status"] == 400


def test_create_report_title_too_long(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.create_report(
        {"headers": auth_headers(token), "body": {"title": "x" * 501}}
    )
    assert resp["status"] == 400


def test_create_report_nul_in_title(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.create_report(
        {"headers": auth_headers(token), "body": {"title": "bad\x00title"}}
    )
    assert resp["status"] == 400


def test_create_report_unauthenticated(svc, conn):
    resp = svc.create_report({"headers": {}, "body": {"title": "X"}})
    assert resp["status"] == 401


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------


def test_get_report_success(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="viewer")
    rid = make_report(conn, tid, uid, "My Report")
    resp = svc.get_report({"headers": auth_headers(token)}, rid)
    assert resp["status"] == 200
    assert resp["body"]["id"] == rid
    assert resp["body"]["title"] == "My Report"


def test_get_report_cross_tenant_returns_404(svc, conn):
    """A report in tenant B must not be visible to a user in tenant A."""
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a, token_a = make_user(conn, tid_a, role="viewer")
    uid_b, _ = make_user(conn, tid_b, role="editor")
    rid = make_report(conn, tid_b, uid_b, "Tenant B Report")

    resp = svc.get_report({"headers": auth_headers(token_a)}, rid)
    # Must be 404, not 403 — do not leak existence
    assert resp["status"] == 404


def test_get_report_invalid_uuid(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.get_report({"headers": auth_headers(token)}, "not-a-uuid")
    assert resp["status"] == 400


def test_get_report_not_found(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.get_report({"headers": auth_headers(token)}, str(uuid.uuid4()))
    assert resp["status"] == 404


# ---------------------------------------------------------------------------
# list_reports
# ---------------------------------------------------------------------------


def test_list_reports_own_only(svc, conn):
    tid = make_tenant(conn)
    uid_a, token_a = make_user(conn, tid, role="editor")
    uid_b, _ = make_user(conn, tid, role="editor")
    make_report(conn, tid, uid_a, "A1")
    make_report(conn, tid, uid_a, "A2")
    make_report(conn, tid, uid_b, "B1")

    resp = svc.list_reports({"headers": auth_headers(token_a)})
    assert resp["status"] == 200
    titles = {r["title"] for r in resp["body"]["reports"]}
    assert titles == {"A1", "A2"}
    assert "B1" not in titles


def test_list_reports_empty(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.list_reports({"headers": auth_headers(token)})
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_list_reports_newest_first(svc, conn):
    import time

    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="editor")
    make_report(conn, tid, uid, "First")
    time.sleep(0.01)
    make_report(conn, tid, uid, "Second")

    resp = svc.list_reports({"headers": auth_headers(token)})
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert titles[0] == "Second"


# ---------------------------------------------------------------------------
# search_reports
# ---------------------------------------------------------------------------


def test_search_reports_finds_match(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="viewer")
    make_report(conn, tid, uid, "Annual Budget")
    make_report(conn, tid, uid, "Quarterly Review")

    resp = svc.search_reports(
        {"headers": auth_headers(token), "query": {"q": "Budget"}}
    )
    assert resp["status"] == 200
    assert len(resp["body"]["reports"]) == 1
    assert resp["body"]["reports"][0]["title"] == "Annual Budget"


def test_search_reports_no_match(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="viewer")
    make_report(conn, tid, uid, "Annual Budget")

    resp = svc.search_reports(
        {"headers": auth_headers(token), "query": {"q": "xyz_no_match"}}
    )
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_search_reports_sort_title(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="viewer")
    make_report(conn, tid, uid, "Zebra Report")
    make_report(conn, tid, uid, "Alpha Report")

    resp = svc.search_reports(
        {"headers": auth_headers(token), "query": {"q": "Report", "sort": "title"}}
    )
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert titles == sorted(titles, reverse=True)


def test_search_reports_invalid_sort_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.search_reports(
        {"headers": auth_headers(token), "query": {"q": "x", "sort": "1; DROP TABLE reports--"}}
    )
    assert resp["status"] == 400


def test_search_reports_like_metachar_escaped(svc, conn):
    """A query of '%' must not match everything."""
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="viewer")
    make_report(conn, tid, uid, "Normal Report")

    resp = svc.search_reports(
        {"headers": auth_headers(token), "query": {"q": "%"}}
    )
    assert resp["status"] == 200
    # '%' is escaped to '\%' so it matches a literal percent, not a wildcard
    assert resp["body"]["reports"] == []


def test_search_reports_cross_tenant_isolation(svc, conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a, token_a = make_user(conn, tid_a, role="viewer")
    uid_b, _ = make_user(conn, tid_b, role="editor")
    make_report(conn, tid_b, uid_b, "Secret B Report")

    resp = svc.search_reports(
        {"headers": auth_headers(token_a), "query": {"q": "Secret"}}
    )
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


# ---------------------------------------------------------------------------
# delete_report
# ---------------------------------------------------------------------------


def test_delete_report_admin_success(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="admin")
    rid = make_report(conn, tid, uid)

    resp = svc.delete_report({"headers": auth_headers(token)}, rid)
    assert resp["status"] == 200
    assert resp["body"]["deleted"] is True

    # Confirm gone
    resp2 = svc.get_report({"headers": auth_headers(token)}, rid)
    assert resp2["status"] == 404


def test_delete_report_editor_forbidden(svc, conn):
    tid = make_tenant(conn)
    uid, token = make_user(conn, tid, role="editor")
    rid = make_report(conn, tid, uid)
    resp = svc.delete_report({"headers": auth_headers(token)}, rid)
    assert resp["status"] == 403


def test_delete_report_cross_tenant_returns_404(svc, conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a, token_a = make_user(conn, tid_a, role="admin")
    uid_b, _ = make_user(conn, tid_b, role="editor")
    rid = make_report(conn, tid_b, uid_b)

    resp = svc.delete_report({"headers": auth_headers(token_a)}, rid)
    assert resp["status"] == 404
