"""Tests for upload_attachment."""

import pytest
from tests.conftest import (
    make_tenant, make_user, make_session, make_report, auth_header
)

_PDF_MAGIC = b"%PDF-1.4 " + b"\x00" * 100   # minimal PDF-like bytes (no MZ/ELF/PHP)


def _upload(service, token, report_id, filename="doc.pdf",
            content_type="application/pdf", data=_PDF_MAGIC):
    return service.upload_attachment({
        "headers": auth_header(token),
        "body": {
            "report_id":    report_id,
            "filename":     filename,
            "content_type": content_type,
            "data":         data,
        },
    })


def test_upload_success(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = _upload(service, token, rid)
    assert resp["status"] == 201
    assert "attachment_id" in resp["body"]


def test_upload_viewer_forbidden(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="viewer")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = _upload(service, token, rid)
    assert resp["status"] == 403


def test_upload_rejects_eicar(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}" + b"}" * 50
    resp = _upload(service, token, rid, data=eicar)
    assert resp["status"] == 422


def test_upload_rejects_pe_executable(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    pe = b"MZ" + b"\x00" * 200
    resp = _upload(service, token, rid, data=pe, filename="evil.exe",
                   content_type="application/pdf")
    assert resp["status"] == 422


def test_upload_rejects_disallowed_content_type(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = _upload(service, token, rid,
                   content_type="application/x-executable",
                   data=b"\x00" * 10)
    assert resp["status"] == 400


def test_upload_rejects_path_traversal_filename(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = _upload(service, token, rid, filename="../../etc/passwd")
    assert resp["status"] == 400


def test_upload_rejects_oversized(service, conn):
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    big = b"\x00" * (25 * 1024 * 1024 + 1)
    resp = _upload(service, token, rid, data=big)
    assert resp["status"] == 400


def test_upload_cross_tenant_report_404(service, conn):
    tid_a = make_tenant(conn)
    tid_b = make_tenant(conn)
    uid_a = make_user(conn, tid_a, role="editor")
    uid_b = make_user(conn, tid_b, role="editor")
    token_a = make_session(conn, uid_a)
    rid_b   = make_report(conn, tid_b, uid_b)

    resp = _upload(service, token_a, rid_b)
    assert resp["status"] == 404


def test_upload_storage_key_is_uuid(service, conn):
    """Storage key must be a server-generated UUID, not derived from filename."""
    import uuid as _uuid
    tid = make_tenant(conn)
    uid = make_user(conn, tid, role="editor")
    token = make_session(conn, uid)
    rid = make_report(conn, tid, uid)

    resp = _upload(service, token, rid, filename="../evil.pdf")
    # Filename with path separator is rejected
    assert resp["status"] == 400

    # Successful upload: verify storage key is a valid UUID
    resp2 = _upload(service, token, rid, filename="safe.pdf")
    assert resp2["status"] == 201
    keys = list(service._attachment_store_dict.keys())
    assert len(keys) == 1
    _uuid.UUID(keys[0])   # raises ValueError if not a UUID
