"""Input validation unit tests."""

from __future__ import annotations

import pytest

from reportkit.errors import BadRequest
from reportkit.validation import (
    validate_filename,
    validate_role,
    validate_search_query,
    validate_sort,
    validate_title,
    require_uuid,
)


# ---------------------------------------------------------------------------
# validate_title
# ---------------------------------------------------------------------------


def test_title_valid():
    assert validate_title("Q1 Report 2025") == "Q1 Report 2025"


def test_title_empty_rejected():
    with pytest.raises(BadRequest):
        validate_title("")


def test_title_too_long_rejected():
    with pytest.raises(BadRequest):
        validate_title("x" * 501)


def test_title_nul_rejected():
    with pytest.raises(BadRequest):
        validate_title("bad\x00title")


# ---------------------------------------------------------------------------
# validate_sort
# ---------------------------------------------------------------------------


def test_sort_created_at():
    assert validate_sort("created_at") == "r.created_at"


def test_sort_title():
    assert validate_sort("title") == "r.title"


def test_sort_invalid_rejected():
    with pytest.raises(BadRequest):
        validate_sort("1; DROP TABLE reports--")


def test_sort_none_returns_default():
    from reportkit.validation import SORT_COLUMN_MAP, DEFAULT_SORT
    assert validate_sort(None) == SORT_COLUMN_MAP[DEFAULT_SORT]


# ---------------------------------------------------------------------------
# validate_filename
# ---------------------------------------------------------------------------


def test_filename_valid():
    assert validate_filename("report.pdf") == "report.pdf"


def test_filename_path_traversal_rejected():
    with pytest.raises(BadRequest):
        validate_filename("../../../etc/passwd")


def test_filename_backslash_rejected():
    with pytest.raises(BadRequest):
        validate_filename("foo\\bar.txt")


def test_filename_nul_rejected():
    with pytest.raises(BadRequest):
        validate_filename("file\x00.txt")


def test_filename_windows_reserved_rejected():
    with pytest.raises(BadRequest):
        validate_filename("CON.txt")


def test_filename_colon_rejected():
    with pytest.raises(BadRequest):
        validate_filename("file:stream.txt")


# ---------------------------------------------------------------------------
# validate_search_query
# ---------------------------------------------------------------------------


def test_search_query_escapes_percent():
    result = validate_search_query("%")
    assert "\\%" in result
    assert result == "\\%"


def test_search_query_escapes_underscore():
    result = validate_search_query("_")
    assert "\\_" in result


def test_search_query_too_long_rejected():
    with pytest.raises(BadRequest):
        validate_search_query("x" * 201)


# ---------------------------------------------------------------------------
# require_uuid
# ---------------------------------------------------------------------------


def test_require_uuid_valid():
    import uuid
    u = str(uuid.uuid4())
    assert require_uuid(u, "id") == u


def test_require_uuid_invalid():
    with pytest.raises(BadRequest):
        require_uuid("not-a-uuid", "id")


def test_require_uuid_non_string():
    with pytest.raises(BadRequest):
        require_uuid(12345, "id")


# ---------------------------------------------------------------------------
# validate_role
# ---------------------------------------------------------------------------


def test_validate_role_valid():
    for r in ("viewer", "editor", "admin"):
        assert validate_role(r) == r


def test_validate_role_invalid():
    with pytest.raises(BadRequest):
        validate_role("superuser")
