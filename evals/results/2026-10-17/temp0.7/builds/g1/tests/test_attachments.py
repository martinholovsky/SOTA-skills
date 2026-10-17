"""Attachment upload tests."""

import pytest

from reportkit.scanner import _EICAR
from tests.conftest import make_request


def _create_report(service, token):
    req = make_request(token, body={"title": "Attach Test", "body": ""})
    return service.create_report(req)["body"]["id"]


class TestUploadAttachment:
    def test_editor_can_upload(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "report.pdf",
            "content_type": "application/pdf",
            "data":         b"PDF content here",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 201
        assert "storage_key" in resp["body"]
        # Storage key is server-generated, not the original filename
        assert resp["body"]["storage_key"] != "report.pdf"

    def test_viewer_cannot_upload(self, service, viewer, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(viewer["token"], body={
            "report_id":    rid,
            "filename":     "x.pdf",
            "content_type": "application/pdf",
            "data":         b"data",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 403

    def test_oversized_upload_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        big = b"x" * (25 * 1024 * 1024 + 1)
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "big.bin",
            "content_type": "application/octet-stream",
            "data":         big,
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 413

    def test_eicar_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "eicar.txt",
            "content_type": "text/plain",
            "data":         _EICAR,
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 422

    def test_path_traversal_filename_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "../../etc/passwd",
            "content_type": "text/plain",
            "data":         b"data",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 400

    def test_cross_tenant_report_is_404(self, service, editor, other_editor):
        rid = _create_report(service, other_editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "x.pdf",
            "content_type": "application/pdf",
            "data":         b"data",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 404

    def test_empty_data_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "empty.pdf",
            "content_type": "application/pdf",
            "data":         b"",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 400

    def test_invalid_content_type_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "x.pdf",
            "content_type": "<script>alert(1)</script>",
            "data":         b"data",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 400

    def test_nul_in_filename_rejected(self, service, editor):
        rid = _create_report(service, editor["token"])
        req = make_request(editor["token"], body={
            "report_id":    rid,
            "filename":     "file\x00.pdf",
            "content_type": "application/pdf",
            "data":         b"data",
        })
        resp = service.upload_attachment(req)
        assert resp["status"] == 400
