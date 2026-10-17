"""Tests for upload_attachment."""
import pytest
from tests.conftest import req
from reportkit import fixtures as F
from reportkit.content_scanner import DisallowedContentError


def test_upload_attachment_success(svc, conn, tenant, editor):
    uid, token = editor
    rid = F.make_report(conn, tenant, uid, title="R")
    data = b"hello world"
    resp = svc.upload_attachment(req(token, body={
        "report_id": rid,
        "filename":  "hello.txt",
        "mime_type": "text/plain",
        "data":      data,
    }))
    assert resp["status"] == 201
    assert resp["attachment"]["size_bytes"] == len(data)
    assert resp["attachment"]["filename"] == "hello.txt"


def test_upload_attachment_too_large(svc, conn, tenant, editor):
    uid, token = editor
    rid = F.make_report(conn, tenant, uid, title="R")
    big = b"x" * (25 * 1024 * 1024 + 1)
    resp = svc.upload_attachment(req(token, body={
        "report_id": rid,
        "filename":  "big.bin",
        "data":      big,
    }))
    assert resp["status"] == 413


def test_upload_attachment_disallowed_content(svc, conn, tenant, editor):
    uid, token = editor
    rid = F.make_report(conn, tenant, uid, title="R")
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    resp = svc.upload_attachment(req(token, body={
        "report_id": rid,
        "filename":  "evil.txt",
        "data":      eicar,
    }))
    assert resp["status"] == 422


def test_upload_attachment_missing_report(svc, editor):
    _, token = editor
    resp = svc.upload_attachment(req(token, body={
        "report_id": "00000000-0000-0000-0000-000000000000",
        "data":      b"data",
    }))
    assert resp["status"] == 404


def test_upload_attachment_missing_report_id(svc, editor):
    _, token = editor
    resp = svc.upload_attachment(req(token, body={"data": b"x"}))
    assert resp["status"] == 400


def test_upload_attachment_viewer_forbidden(svc, conn, tenant, viewer, editor):
    e_uid, e_token = editor
    _, v_token = viewer
    rid = F.make_report(conn, tenant, e_uid, title="R")
    from reportkit.auth import PermissionError
    with pytest.raises(PermissionError):
        svc.upload_attachment(req(v_token, body={
            "report_id": rid,
            "data":      b"x",
        }))


def test_upload_elf_rejected(svc, conn, tenant, editor):
    uid, token = editor
    rid = F.make_report(conn, tenant, uid, title="R")
    elf_data = b"\x7fELF" + b"\x00" * 100
    resp = svc.upload_attachment(req(token, body={
        "report_id": rid,
        "filename":  "binary",
        "data":      elf_data,
    }))
    assert resp["status"] == 422
