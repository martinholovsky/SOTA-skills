"""Attachment upload tests."""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, make_tenant, make_user


def _req(token: str, filename: str, data: bytes) -> dict:
    return {
        "headers": auth_headers(token),
        "files": {"file": {"filename": filename, "data": data}},
    }


def test_upload_clean_file(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "report.pdf", b"%PDF-1.4 clean content"))
    assert resp["status"] == 201
    assert resp["body"]["scan_status"] == "clean"
    assert resp["body"]["filename"] == "report.pdf"


def test_upload_elf_binary_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "evil.bin", b"\x7fELF\x02\x01\x01"))
    assert resp["status"] == 400
    assert "scan" in resp["body"]["message"]


def test_upload_pe_binary_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "evil.exe", b"MZ\x90\x00"))
    assert resp["status"] == 400


def test_upload_shebang_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "script.sh", b"#!/bin/bash\nrm -rf /"))
    assert resp["status"] == 400


def test_upload_exceeds_size_limit(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    big = b"x" * (25 * 1024 * 1024 + 1)
    resp = svc.upload_attachment(_req(token, "big.bin", big))
    assert resp["status"] == 400
    assert "size" in resp["body"]["message"]


def test_upload_empty_file_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "empty.txt", b""))
    assert resp["status"] == 400


def test_upload_path_traversal_filename_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "../../../etc/passwd", b"data"))
    assert resp["status"] == 400


def test_upload_nul_in_filename_rejected(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "file\x00.txt", b"data"))
    assert resp["status"] == 400


def test_upload_viewer_forbidden(svc, conn):
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="viewer")
    resp = svc.upload_attachment(_req(token, "f.txt", b"data"))
    assert resp["status"] == 403


def test_upload_storage_key_is_uuid_not_filename(svc, conn):
    """The storage key must be server-generated, not derived from the filename."""
    tid = make_tenant(conn)
    _, token = make_user(conn, tid, role="editor")
    resp = svc.upload_attachment(_req(token, "myfile.txt", b"hello world"))
    assert resp["status"] == 201
    att_id = resp["body"]["id"]
    row = conn.execute(
        "SELECT storage_key FROM attachments WHERE id = ?", (att_id,)
    ).fetchone()
    assert row["storage_key"] != "myfile.txt"
    # storage_key should be a UUID
    import uuid
    uuid.UUID(row["storage_key"])  # raises if not valid UUID
