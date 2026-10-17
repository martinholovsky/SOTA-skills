"""Tests for list_reports."""

import pytest
from tests.conftest import (
    make_tenant, make_user, make_session, make_report, auth_header
)


def test_list_returns_own_reports_only(service, conn):
    tid = make_tenant(conn)
    uid_a = make_user(conn, tid, role="viewer")
    uid_b = make_user(conn, tid, role="viewer")
    token_a = make_session(conn, uid_a)

    rid1 = make_report(conn, tid, uid_a, title="A1")
    rid2 = make_report(conn, tid, uid_a, title="A2")
    _rid_b = make_report(conn, tid, uid_b, title="B1")

    resp = service.list_reports({"headers": auth_header(token_a)})
    assert resp["status"] == 200
    ids = {r["id"] for r in resp["body"]["reports"]}
    assert rid1 in ids
    assert rid2 in ids
    assert _rid_b not in ids


def test_list_cross_tenant_isolation(service, conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a, role="viewer")
    uid_b = make_user(conn, tid_b, role="viewer")
    token_a = make_session(conn, uid_a)
    rid_b   = make_report(conn, tid_b, uid_b)

    resp = service.list_reports({"headers": auth_header(token_a)})
    assert resp["status"] == 200
    ids = {r["id"] for r in resp["body"]["reports"]}
    assert rid_b not in ids


def test_list_empty(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = service.list_reports({"headers": auth_header(token)})
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_list_unauthenticated(service):
    resp = service.list_reports({"headers": {}})
    assert resp["status"] == 401
