"""Tests for get_report — including tenant isolation."""

import uuid
import pytest
from tests.conftest import (
    make_tenant, make_user, make_session, make_report, auth_header
)


def test_get_own_report(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid, title="Hello")

    resp = service.get_report({"headers": auth_header(token)}, rid)
    assert resp["status"] == 200
    assert resp["body"]["title"] == "Hello"


def test_get_report_wrong_tenant_returns_404(service, conn):
    """A report in tenant B must not be visible to a user in tenant A."""
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a, role="viewer")
    uid_b = make_user(conn, tid_b, role="viewer")
    token_a = make_session(conn, uid_a)
    rid_b   = make_report(conn, tid_b, uid_b)

    resp = service.get_report({"headers": auth_header(token_a)}, rid_b)
    # Must be 404, not 403 (do not leak existence)
    assert resp["status"] == 404


def test_get_nonexistent_report_404(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = service.get_report({"headers": auth_header(token)}, str(uuid.uuid4()))
    assert resp["status"] == 404


def test_get_report_invalid_uuid(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)

    resp = service.get_report({"headers": auth_header(token)}, "not-a-uuid")
    assert resp["status"] == 400


def test_get_report_unauthenticated(service):
    resp = service.get_report({"headers": {}}, str(uuid.uuid4()))
    assert resp["status"] == 401
