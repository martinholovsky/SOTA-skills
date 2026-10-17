"""
Tests for input validation helpers.
"""

import pytest

from reportkit.errors import BadRequest
from reportkit.validation import (
    require_string,
    require_title,
    require_body,
    require_uuid,
    require_sort_key,
    require_filename,
    require_mime_type,
    require_bytes,
    extract_bearer_token,
)
from reportkit.errors import Unauthorized


class TestRequireString:
    def test_valid(self):
        assert require_string("hello", "f") == "hello"

    def test_too_short(self):
        with pytest.raises(BadRequest):
            require_string("", "f", min_len=1)

    def test_too_long(self):
        with pytest.raises(BadRequest):
            require_string("x" * 501, "f", max_len=500)

    def test_nul_rejected(self):
        with pytest.raises(BadRequest):
            require_string("bad\x00", "f")

    def test_nfc_normalization(self):
        # Composed and decomposed forms of é should both be accepted and
        # normalized to NFC.
        composed = "\u00e9"
        decomposed = "e\u0301"
        assert require_string(decomposed, "f") == composed


class TestRequireTitle:
    def test_valid(self):
        assert require_title("My Report 2024") == "My Report 2024"

    def test_empty_raises(self):
        with pytest.raises(BadRequest):
            require_title("")

    def test_too_long_raises(self):
        with pytest.raises(BadRequest):
            require_title("x" * 501)


class TestRequireUUID:
    def test_valid_uuid(self):
        v = "550e8400-e29b-41d4-a716-446655440000"
        assert require_uuid(v) == v

    def test_invalid_raises(self):
        with pytest.raises(BadRequest):
            require_uuid("not-a-uuid")

    def test_non_v4_raises(self):
        with pytest.raises(BadRequest):
            require_uuid("550e8400-e29b-31d4-a716-446655440000")  # v3


class TestRequireSortKey:
    def test_valid_created_at(self):
        assert require_sort_key("created_at") == "created_at"

    def test_valid_title(self):
        assert require_sort_key("title") == "title"

    def test_injection_attempt_raises(self):
        with pytest.raises(BadRequest):
            require_sort_key("created_at; DROP TABLE reports")

    def test_unknown_key_raises(self):
        with pytest.raises(BadRequest):
            require_sort_key("owner_id")


class TestRequireFilename:
    def test_valid(self):
        assert require_filename("report.pdf") == "report.pdf"

    def test_path_traversal_raises(self):
        with pytest.raises(BadRequest):
            require_filename("../../etc/passwd")

    def test_absolute_path_raises(self):
        with pytest.raises(BadRequest):
            require_filename("/etc/passwd")

    def test_nul_raises(self):
        with pytest.raises(BadRequest):
            require_filename("bad\x00.pdf")

    def test_colon_raises(self):
        with pytest.raises(BadRequest):
            require_filename("file:stream")

    def test_empty_raises(self):
        with pytest.raises(BadRequest):
            require_filename("")


class TestRequireMimeType:
    def test_valid(self):
        assert require_mime_type("application/pdf") == "application/pdf"

    def test_invalid_raises(self):
        with pytest.raises(BadRequest):
            require_mime_type("not a mime type!!!")

    def test_with_parameters_raises(self):
        # Parameters (e.g. charset) are not accepted; callers strip them first.
        with pytest.raises(BadRequest):
            require_mime_type("text/plain; charset=utf-8")


class TestRequireBytes:
    def test_valid(self):
        assert require_bytes(b"hello", "f", 100) == b"hello"

    def test_too_large_raises(self):
        with pytest.raises(BadRequest):
            require_bytes(b"x" * 101, "f", 100)

    def test_non_bytes_raises(self):
        with pytest.raises(BadRequest):
            require_bytes("string", "f", 100)  # type: ignore[arg-type]


class TestExtractBearerToken:
    def test_valid(self):
        req = {"headers": {"Authorization": "Bearer mytoken123"}}
        assert extract_bearer_token(req) == "mytoken123"

    def test_case_insensitive_header(self):
        req = {"headers": {"authorization": "Bearer tok"}}
        assert extract_bearer_token(req) == "tok"

    def test_missing_header_raises(self):
        with pytest.raises(Unauthorized):
            extract_bearer_token({"headers": {}})

    def test_wrong_scheme_raises(self):
        with pytest.raises(Unauthorized):
            extract_bearer_token({"headers": {"Authorization": "Basic abc"}})

    def test_empty_token_raises(self):
        with pytest.raises(Unauthorized):
            extract_bearer_token({"headers": {"Authorization": "Bearer "}})
