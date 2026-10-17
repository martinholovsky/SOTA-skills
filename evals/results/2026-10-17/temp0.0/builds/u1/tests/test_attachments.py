"""Attachment upload tests."""

import pytest
from tests.conftest import make_request
from reportkit.attachments import MAX_ATTACHMENT_BYTES


def _create_report(svc, token, title="Test Report"):
    resp = svc.create_report(make_request(token, body={"title": title}))
    assert resp["status"] == 201
    return resp["report"]["id"]


def test_upload_attachment_success(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    req = make_request(
        editor_token,
        body={
            "report_id": report_id,
            "filename": "data.csv",
            "mime_type": "text/csv",
            "data": b"col1,col2\n1,2\n",
        },
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 201
    assert resp["attachment"]["filename"] == "data.csv"
    assert resp["attachment"]["size_bytes"] == len(b"col1,col2\n1,2\n")


def test_upload_attachment_too_large(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    big_data = b"x" * (MAX_ATTACHMENT_BYTES + 1)
    req = make_request(
        editor_token,
        body={"report_id": report_id, "filename": "big.bin", "data": big_data},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 413


def test_upload_attachment_eicar_rejected(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    eicar = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" + b"!" * 10
    req = make_request(
        editor_token,
        body={"report_id": report_id, "filename": "virus.txt", "data": eicar},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 422


def test_upload_attachment_pe_header_rejected(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    pe_data = b"\x4d\x5a\x90\x00" + b"\x00" * 100
    req = make_request(
        editor_token,
        body={"report_id": report_id, "filename": "evil.exe", "data": pe_data},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 422


def test_upload_attachment_missing_report(svc, editor_token):
    req = make_request(
        editor_token,
        body={"report_id": "no-such-report", "filename": "f.txt", "data": b"hello"},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 404


def test_upload_attachment_viewer_forbidden(svc, viewer_token, editor_token):
    report_id = _create_report(svc, editor_token)
    req = make_request(
        viewer_token,
        body={"report_id": report_id, "filename": "f.txt", "data": b"hello"},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 403


def test_upload_attachment_missing_filename(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    req = make_request(
        editor_token,
        body={"report_id": report_id, "data": b"hello"},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 400


def test_upload_attachment_empty_data(svc, editor_token):
    report_id = _create_report(svc, editor_token)
    req = make_request(
        editor_token,
        body={"report_id": report_id, "filename": "empty.txt", "data": b""},
    )
    resp = svc.upload_attachment(req)
    assert resp["status"] == 400
