"""Tests for search_reports — including SQL injection and sort allowlist."""

import pytest
from tests.conftest import (
    make_tenant, make_user, make_session, make_report, auth_header
)


def _search(service, token, q, sort="created_at"):
    return service.search_reports({
        "headers": auth_header(token),
        "query":   {"q": q, "sort": sort},
    })


def test_search_finds_matching_title(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    make_report(conn, tid, uid, title="Annual Report 2024")
    make_report(conn, tid, uid, title="Quarterly Summary")

    resp = _search(service, token, "Annual")
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert "Annual Report 2024" in titles
    assert "Quarterly Summary" not in titles


def test_search_sql_injection_in_query(service, conn):
    """A LIKE-injection attempt must not return extra rows."""
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    make_report(conn, tid, uid, title="Safe Report")
    make_report(conn, tid, uid, title="Other")

    # '%' would match everything if not escaped.
    resp = _search(service, token, "%")
    assert resp["status"] == 200
    # '%' is escaped to '\%', which matches nothing literally.
    assert resp["body"]["reports"] == []


def test_search_like_wildcard_escaped(service, conn):
    """Underscore metachar must be escaped."""
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    make_report(conn, tid, uid, title="a_b")
    make_report(conn, tid, uid, title="axb")

    # Searching for literal "a_b" should only match "a_b", not "axb".
    resp = _search(service, token, "a_b")
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert "a_b" in titles
    assert "axb" not in titles


def test_search_invalid_sort_key(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = _search(service, token, "x", sort="'; DROP TABLE reports; --")
    assert resp["status"] == 400


def test_search_valid_sort_title(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    make_report(conn, tid, uid, title="Zebra")
    make_report(conn, tid, uid, title="Apple")

    resp = _search(service, token, "e", sort="title")
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["body"]["reports"]]
    assert titles == sorted(titles)


def test_search_empty_query_rejected(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = _search(service, token, "")
    assert resp["status"] == 400


def test_search_cross_tenant_isolation(service, conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a, role="viewer")
    uid_b = make_user(conn, tid_b, role="viewer")
    token_a = make_session(conn, uid_a)
    make_report(conn, tid_b, uid_b, title="Secret B Report")

    resp = _search(service, token_a, "Secret")
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_search_unauthenticated(service):
    resp = service.search_reports({"headers": {}, "query": {"q": "x"}})
    assert resp["status"] == 401
