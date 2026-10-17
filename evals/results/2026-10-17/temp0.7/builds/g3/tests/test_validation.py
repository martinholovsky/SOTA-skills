"""Unit tests for the validation layer."""

import pytest
from reportkit.validation import (
    require_string,
    require_uuid,
    validate_sort_key,
    validate_filename,
    validate_content_type,
    validate_attachment_size,
    ValidationError,
    MAX_ATTACH_BYTES,
)


# --- require_string ---

def test_require_string_ok():
    assert require_string("hello", "f", max_len=10) == "hello"


def test_require_string_nfc_normalised():
    # Composed vs decomposed form of é
    decomposed = "e\u0301"
    result = require_string(decomposed, "f", max_len=10)
    assert result == "\xe9"   # NFC form


def test_require_string_too_long():
    with pytest.raises(ValidationError, match="exceeds"):
        require_string("x" * 201, "f", max_len=200)


def test_require_string_nul_rejected():
    with pytest.raises(ValidationError):
        require_string("bad\x00", "f", max_len=100)


def test_require_string_empty_rejected():
    with pytest.raises(ValidationError, match="empty"):
        require_string("   ", "f", max_len=100)


# --- require_uuid ---

def test_require_uuid_valid():
    v = "550e8400-e29b-41d4-a716-446655440000"
    assert require_uuid(v, "id") == v


def test_require_uuid_invalid():
    with pytest.raises(ValidationError):
        require_uuid("not-a-uuid", "id")


def test_require_uuid_non_string():
    with pytest.raises(ValidationError):
        require_uuid(123, "id")


# --- validate_sort_key ---

def test_sort_key_valid():
    assert validate_sort_key("created_at") == "r.created_at"
    assert validate_sort_key("title")      == "r.title"


def test_sort_key_injection_rejected():
    with pytest.raises(ValidationError):
        validate_sort_key("'; DROP TABLE reports; --")


def test_sort_key_unknown_rejected():
    with pytest.raises(ValidationError):
        validate_sort_key("owner_id")


# --- validate_filename ---

def test_filename_ok():
    assert validate_filename("report.pdf") == "report.pdf"


def test_filename_path_traversal_rejected():
    with pytest.raises(ValidationError):
        validate_filename("../../etc/passwd")


def test_filename_absolute_rejected():
    with pytest.raises(ValidationError):
        validate_filename("/etc/passwd")


def test_filename_windows_reserved():
    with pytest.raises(ValidationError):
        validate_filename("CON.txt")


def test_filename_nul_rejected():
    with pytest.raises(ValidationError):
        validate_filename("file\x00.pdf")


def test_filename_colon_rejected():
    with pytest.raises(ValidationError):
        validate_filename("file:stream")


# --- validate_content_type ---

def test_content_type_pdf_ok():
    assert validate_content_type("application/pdf") == "application/pdf"


def test_content_type_with_params_stripped():
    assert validate_content_type("text/plain; charset=utf-8") == "text/plain"


def test_content_type_disallowed():
    with pytest.raises(ValidationError):
        validate_content_type("application/x-executable")


# --- validate_attachment_size ---

def test_size_ok():
    validate_attachment_size(1024)


def test_size_too_large():
    with pytest.raises(ValidationError):
        validate_attachment_size(MAX_ATTACH_BYTES + 1)


def test_size_zero_rejected():
    with pytest.raises(ValidationError):
        validate_attachment_size(0)


def test_size_negative_rejected():
    with pytest.raises(ValidationError):
        validate_attachment_size(-1)
