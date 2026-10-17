"""Tests for create_report."""

import pytest
from tests.conftest import make_tenant, make_user, make_session, auth_header


def test_create_report_success(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    resp = service.create_report({
        "headers": auth_header(token),
        "body": {"title": "My Report", "body": "content"},
    })
    assert resp["status"] == 201
    assert "report_id" in resp["body"]


def test_create_report_viewer_forbidden(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = service.create_report({
        "headers": auth_header(token),
        "body": {"title": "T", "body": "b"},
    })
    assert resp["status"] == 403


def test_create_report_missing_title(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    resp = service.create_report({
        "headers": auth_header(token),
        "body": {"body": "no title"},
    })
    assert resp["status"] == 400


def test_create_report_title_too_long(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    resp = service.create_report({
        "headers": auth_header(token),
        "body": {"title": "x" * 201, "body": "b"},
    })
    assert resp["status"] == 400


def test_create_report_unauthenticated(service):
    resp = service.create_report({"headers": {}, "body": {"title": "T", "body": "b"}})
    assert resp["status"] == 401


def test_create_report_nul_in_title(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)

    resp = service.create_report({
        "headers": auth_header(token),
        "body": {"title": "bad\x00title", "body": "b"},
    })
    assert resp["status"] == 400
