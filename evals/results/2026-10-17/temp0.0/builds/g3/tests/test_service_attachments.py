"""
Tests for upload_attachment.
"""

import pytest

from reportkit.errors import BadRequest, Forbidden, UnsupportedMediaType
from tests.conftest import make_user, auth_headers


def _pdf_bytes() -> bytes:
    # Minimal valid-looking PDF header.
    return b"%PDF-1.4 minimal"


def _eicar() -> bytes:
    return b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


class TestUploadAttachment:
    def test_clean_upload_succeeds(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        resp = service.upload_attachment({
            "headers": auth_headers(token),
            "files": {
                "file": {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "data": _pdf_bytes(),
                }
            },
        })
        assert resp["status"] == 201
        assert "id" in resp["body"]
        assert "storage_key" in resp["body"]
        # storage_key is server-generated, not the user filename.
        assert resp["body"]["storage_key"] != "report.pdf"

    def test_viewer_cannot_upload(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "viewer")
        with pytest.raises(Forbidden):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "x.pdf",
                        "content_type": "application/pdf",
                        "data": _pdf_bytes(),
                    }
                },
            })

    def test_disallowed_mime_type_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(UnsupportedMediaType):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "script.exe",
                        "content_type": "application/x-msdownload",
                        "data": b"MZ",
                    }
                },
            })

    def test_eicar_rejected(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest, match="rejected"):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "eicar.txt",
                        "content_type": "text/plain",
                        "data": _eicar(),
                    }
                },
            })

    def test_oversized_file_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "big.pdf",
                        "content_type": "application/pdf",
                        "data": b"x" * (25 * 1024 * 1024 + 1),
                    }
                },
            })

    def test_path_traversal_filename_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "../../etc/passwd",
                        "content_type": "text/plain",
                        "data": b"data",
                    }
                },
            })

    def test_nul_in_filename_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "bad\x00name.pdf",
                        "content_type": "application/pdf",
                        "data": _pdf_bytes(),
                    }
                },
            })

    def test_missing_file_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {},
            })

    def test_invalid_content_type_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.upload_attachment({
                "headers": auth_headers(token),
                "files": {
                    "file": {
                        "filename": "x.pdf",
                        "content_type": "not a mime type!!!",
                        "data": _pdf_bytes(),
                    }
                },
            })
