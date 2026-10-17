"""Validation unit tests — allowlist, injection probes, boundary cases."""

import pytest

from reportkit.validation import (
    validate_uuid,
    validate_title,
    validate_body,
    validate_sort,
    validate_search_query,
    validate_role,
    validate_mime_type,
    validate_filename,
    ValidationError,
)


# ---------------------------------------------------------------------------
# UUID
# ---------------------------------------------------------------------------

def test_valid_uuid():
    v = "123e4567-e89b-12d3-a456-426614174000"
    assert validate_uuid(v) == v


def test_invalid_uuid_rejected():
    with pytest.raises(ValidationError):
        validate_uuid("not-a-uuid")


def test_uuid_nul_rejected():
    with pytest.raises(ValidationError):
        validate_uuid("123e4567-e89b-12d3-a456-42661417400\x00")


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

def test_valid_title():
    assert validate_title("My Report 2024") == "My Report 2024"


def test_title_too_long():
    with pytest.raises(ValidationError):
        validate_title("x" * 257)


def test_title_nul_rejected():
    with pytest.raises(ValidationError):
        validate_title("abc\x00def")


def test_empty_title_rejected():
    with pytest.raises(ValidationError):
        validate_title("")


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def test_body_too_long():
    with pytest.raises(ValidationError):
        validate_body("x" * 65537)


def test_body_nul_rejected():
    with pytest.raises(ValidationError):
        validate_body("text\x00text")


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------

def test_sort_created_at():
    assert "created_at" in validate_sort("created_at")


def test_sort_title():
    assert "title" in validate_sort("title")


def test_sort_injection_rejected():
    with pytest.raises(ValidationError):
        validate_sort("1; DROP TABLE reports--")


def test_sort_unknown_key_rejected():
    with pytest.raises(ValidationError):
        validate_sort("id")


# ---------------------------------------------------------------------------
# Search query
# ---------------------------------------------------------------------------

def test_search_query_valid():
    assert validate_search_query("hello world") == "hello world"


def test_search_query_too_long():
    with pytest.raises(ValidationError):
        validate_search_query("x" * 129)


def test_search_query_nul_rejected():
    with pytest.raises(ValidationError):
        validate_search_query("abc\x00")


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

def test_valid_roles():
    for r in ("viewer", "editor", "admin"):
        assert validate_role(r) == r


def test_invalid_role():
    with pytest.raises(ValidationError):
        validate_role("superuser")


# ---------------------------------------------------------------------------
# MIME type
# ---------------------------------------------------------------------------

def test_valid_mime():
    assert validate_mime_type("application/pdf") == "application/pdf"


def test_disallowed_mime():
    with pytest.raises(ValidationError):
        validate_mime_type("application/x-sh")


def test_mime_nul_rejected():
    with pytest.raises(ValidationError):
        validate_mime_type("text/plain\x00")


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------

def test_valid_filename():
    assert validate_filename("report.pdf") == "report.pdf"


def test_filename_path_sep_rejected():
    with pytest.raises(ValidationError):
        validate_filename("../../etc/passwd")


def test_filename_backslash_rejected():
    with pytest.raises(ValidationError):
        validate_filename("..\\windows\\system32")


def test_filename_colon_rejected():
    with pytest.raises(ValidationError):
        validate_filename("file:stream")


def test_filename_nul_rejected():
    with pytest.raises(ValidationError):
        validate_filename("file\x00.txt")


def test_filename_only_dots_rejected():
    with pytest.raises(ValidationError):
        validate_filename("...")


def test_filename_too_long():
    with pytest.raises(ValidationError):
        validate_filename("x" * 256)
