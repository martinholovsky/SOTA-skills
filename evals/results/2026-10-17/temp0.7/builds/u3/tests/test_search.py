"""Tests for search_reports."""
import pytest
from tests.conftest import req
from reportkit import fixtures as F


def test_search_by_title(svc, conn, tenant, editor):
    uid, token = editor
    F.make_report(conn, tenant, uid, title="Annual Budget")
    F.make_report(conn, tenant, uid, title="Quarterly Review")
    resp = svc.search_reports(req(token, query={"q": "budget"}))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 1
    assert resp["reports"][0]["title"] == "Annual Budget"


def test_search_empty_query_returns_all(svc, conn, tenant, editor):
    uid, token = editor
    F.make_report(conn, tenant, uid, title="Alpha")
    F.make_report(conn, tenant, uid, title="Beta")
    resp = svc.search_reports(req(token, query={"q": ""}))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 2


def test_search_sort_by_title(svc, conn, tenant, editor):
    uid, token = editor
    F.make_report(conn, tenant, uid, title="Zebra")
    F.make_report(conn, tenant, uid, title="Apple")
    resp = svc.search_reports(req(token, query={"q": "", "sort": "title"}))
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["reports"]]
    assert titles == sorted(titles)


def test_search_invalid_sort(svc, editor):
    _, token = editor
    resp = svc.search_reports(req(token, query={"sort": "DROP TABLE reports--"}))
    assert resp["status"] == 400


def test_search_sort_default(svc, conn, tenant, editor):
    uid, token = editor
    F.make_report(conn, tenant, uid, title="One")
    resp = svc.search_reports(req(token, query={}))
    assert resp["status"] == 200


def test_search_no_cross_tenant(svc, conn, tenant, editor):
    uid, token = editor
    other_tid = F.make_tenant(conn, "Other")
    other_uid = F.make_user(conn, other_tid)
    F.make_report(conn, other_tid, other_uid, title="Secret Budget")
    resp = svc.search_reports(req(token, query={"q": "budget"}))
    assert resp["status"] == 200
    assert resp["reports"] == []
