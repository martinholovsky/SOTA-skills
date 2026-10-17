"""Attachment upload tests — size limits, MIME checks, scanner."""

import uuid
import pytest

from tests.conftest import _make_user, _req
from reportkit.service import ReportService
from reportkit.models import MAX_ATTACHMENT_BYTES, DISALLOWED_SIGNATURES


def test_upload_valid_attachment(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "report.pdf",
        "mime_type": "application/pdf",
        "data":      b"%PDF-1.4 clean content",
    }))
    assert resp["status"] == 200
    assert "attachment_id" in resp["body"]
    assert "storage_key"   in resp["body"]


def test_upload_too_large(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "big.bin",
        "mime_type": "application/octet-stream",
        "data":      b"x" * (MAX_ATTACHMENT_BYTES + 1),
    }))
    assert resp["status"] == 413


def test_upload_empty_rejected(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "empty.txt",
        "mime_type": "text/plain",
        "data":      b"",
    }))
    assert resp["status"] == 400


def test_upload_eicar_rejected(db, svc, editor):
    _, _, raw = editor
    eicar = DISALLOWED_SIGNATURES[0]  # EICAR test string
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "virus.txt",
        "mime_type": "text/plain",
        "data":      eicar + b" extra",
    }))
    assert resp["status"] == 422


def test_upload_pe_executable_rejected(db, svc, editor):
    _, _, raw = editor
    pe_header = b"\x4d\x5a\x90\x00" + b"\x00" * 100
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "malware.exe",
        "mime_type": "application/octet-stream",
        "data":      pe_header,
    }))
    assert resp["status"] == 422


def test_upload_disallowed_mime(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "script.sh",
        "mime_type": "application/x-sh",
        "data":      b"#!/bin/bash",
    }))
    assert resp["status"] == 400


def test_upload_path_traversal_filename_rejected(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "../../etc/passwd",
        "mime_type": "text/plain",
        "data":      b"content",
    }))
    assert resp["status"] == 400


def test_upload_nul_in_filename_rejected(db, svc, editor):
    _, _, raw = editor
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "file\x00.txt",
        "mime_type": "text/plain",
        "data":      b"content",
    }))
    assert resp["status"] == 400


def test_upload_links_to_report(db, svc, editor):
    _, _, raw = editor
    create = svc.create_report(_req(raw, body={"title": "R", "body": ""}))
    rid = create["body"]["report_id"]
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "attach.pdf",
        "mime_type": "application/pdf",
        "data":      b"%PDF clean",
        "report_id": rid,
    }))
    assert resp["status"] == 200


def test_upload_link_to_other_users_report_rejected(db, svc):
    import uuid as _uuid
    tid = str(_uuid.uuid4())
    _, _, raw_a = _make_user(db, role="editor", tenant_id=tid)
    _, _, raw_b = _make_user(db, role="editor", tenant_id=tid)

    create = svc.create_report(_req(raw_a, body={"title": "A", "body": ""}))
    rid = create["body"]["report_id"]

    resp = svc.upload_attachment(_req(raw_b, body={
        "filename":  "steal.pdf",
        "mime_type": "application/pdf",
        "data":      b"%PDF clean",
        "report_id": rid,
    }))
    assert resp["status"] == 404


def test_viewer_cannot_upload(db, svc, viewer):
    _, _, raw = viewer
    resp = svc.upload_attachment(_req(raw, body={
        "filename":  "f.pdf",
        "mime_type": "application/pdf",
        "data":      b"%PDF clean",
    }))
    assert resp["status"] == 403
