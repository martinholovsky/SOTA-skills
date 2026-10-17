"""Tests for search_reports."""

import pytest
from reportkit.fixtures import make_report, bearer


def _uid(conn, token):
    return conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (token,)
    ).fetchone()["user_id"]


def test_search_finds_matching(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    make_report(conn, uid, tenant, "Annual Budget")
    make_report(conn, uid, tenant, "Monthly Expenses")

    req = {**bearer(editor_token), "query": {"q": "Budget"}}
    resp = svc.search_reports(req)
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert "Annual Budget" in titles
    assert "Monthly Expenses" not in titles


def test_search_empty_query_returns_all(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    make_report(conn, uid, tenant, "Alpha")
    make_report(conn, uid, tenant, "Beta")

    req = {**bearer(editor_token), "query": {"q": ""}}
    resp = svc.search_reports(req)
    assert len(resp["body"]["reports"]) == 2


def test_search_sort_by_title(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    make_report(conn, uid, tenant, "Zebra")
    make_report(conn, uid, tenant, "Apple")

    req = {**bearer(editor_token), "query": {"q": "", "sort": "title"}}
    resp = svc.search_reports(req)
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert titles == sorted(titles, reverse=True)


def test_search_invalid_sort_rejected(svc, editor_token):
    req = {**bearer(editor_token), "query": {"sort": "'; DROP TABLE reports; --"}}
    resp = svc.search_reports(req)
    assert resp["status"] == 422


def test_search_sort_default_is_created_at(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    import time
    make_report(conn, uid, tenant, "First")
    time.sleep(0.01)
    make_report(conn, uid, tenant, "Second")

    req = {**bearer(editor_token), "query": {}}
    resp = svc.search_reports(req)
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert titles[0] == "Second"


def test_search_no_cross_tenant(svc, conn, editor_token):
    from reportkit.fixtures import make_tenant, make_user
    other = make_tenant(conn, "Other")
    ouid  = make_user(conn, other, role="editor")
    make_report(conn, ouid, other, "Secret Report")

    req = {**bearer(editor_token), "query": {"q": "Secret"}}
    resp = svc.search_reports(req)
    assert resp["body"]["reports"] == []
