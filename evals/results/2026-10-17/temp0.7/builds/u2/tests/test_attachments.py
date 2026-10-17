"""Tests for upload_attachment."""

import pytest
from reportkit.fixtures import make_report, bearer
from reportkit.scanner import MAX_ATTACHMENT_BYTES


def _uid(conn, token):
    return conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (token,)
    ).fetchone()["user_id"]


def test_upload_success(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    rid = make_report(conn, uid, tenant)

    req = {
        **bearer(editor_token),
        "body":       {"report_id": rid, "filename": "data.csv", "mime_type": "text/csv"},
        "body_bytes": b"col1,col2\n1,2\n",
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 201
    assert resp["body"]["filename"] == "data.csv"
    assert resp["body"]["size_bytes"] == len(b"col1,col2\n1,2\n")


def test_upload_viewer_forbidden(svc, conn, viewer_token, tenant):
    uid = _uid(conn, viewer_token)
    # Viewer cannot write, so make the report via SQL directly
    rid = make_report(conn, uid, tenant)

    req = {
        **bearer(viewer_token),
        "body":       {"report_id": rid, "filename": "x.txt"},
        "body_bytes": b"hello",
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 403


def test_upload_too_large(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    rid = make_report(conn, uid, tenant)

    big = b"x" * (MAX_ATTACHMENT_BYTES + 1)
    req = {
        **bearer(editor_token),
        "body":       {"report_id": rid, "filename": "big.bin"},
        "body_bytes": big,
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 413


def test_upload_disallowed_content(svc, conn, editor_token, tenant):
    uid = _uid(conn, editor_token)
    rid = make_report(conn, uid, tenant)

    payload = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
    req = {
        **bearer(editor_token),
        "body":       {"report_id": rid, "filename": "evil.txt"},
        "body_bytes": payload,
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 422


def test_upload_missing_report_id(svc, editor_token):
    req = {
        **bearer(editor_token),
        "body":       {"filename": "oops.txt"},
        "body_bytes": b"data",
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 422


def test_upload_report_wrong_tenant(svc, conn, editor_token):
    from reportkit.fixtures import make_tenant, make_user
    other = make_tenant(conn, "Other")
    ouid  = make_user(conn, other, role="editor")
    rid   = make_report(conn, ouid, other)

    req = {
        **bearer(editor_token),
        "body":       {"report_id": rid, "filename": "f.txt"},
        "body_bytes": b"data",
    }
    resp = svc.upload_attachment(req)
    assert resp["status"] == 404
