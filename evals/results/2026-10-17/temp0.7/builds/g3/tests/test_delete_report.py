"""Tests for delete_report."""

import uuid
import pytest
from tests.conftest import (
    make_tenant, make_user, make_session, make_report, auth_header
)


def test_delete_own_report(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = service.delete_report({"headers": auth_header(token)}, rid)
    assert resp["status"] == 204

    # Verify it is gone.
    get_resp = service.get_report({"headers": auth_header(token)}, rid)
    assert get_resp["status"] == 404


def test_delete_requires_admin(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = service.delete_report({"headers": auth_header(token)}, rid)
    assert resp["status"] == 403


def test_delete_cross_tenant_returns_404(service, conn):
    """An admin in tenant A cannot delete a report in tenant B."""
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a, role="admin")
    uid_b = make_user(conn, tid_b, role="admin")
    token_a = make_session(conn, uid_a)
    rid_b   = make_report(conn, tid_b, uid_b)

    resp = service.delete_report({"headers": auth_header(token_a)}, rid_b)
    assert resp["status"] == 404


def test_delete_nonexistent_404(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)

    resp = service.delete_report({"headers": auth_header(token)}, str(uuid.uuid4()))
    assert resp["status"] == 404


def test_delete_invalid_uuid(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="admin")
    token = make_session(conn, uid)

    resp = service.delete_report({"headers": auth_header(token)}, "bad-id")
    assert resp["status"] == 400
