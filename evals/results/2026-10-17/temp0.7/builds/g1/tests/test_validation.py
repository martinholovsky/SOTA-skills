"""Input validation tests."""

import pytest

from reportkit.validation import (
    ValidationError,
    validate_body,
    validate_content_type,
    validate_filename,
    validate_search_query,
    validate_sort_col,
    validate_title,
    validate_uuid,
    SORT_COL_ALLOWLIST,
)


class TestUUID:
    def test_valid(self):
        assert validate_uuid("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa") == \
               "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_uppercase_normalised(self):
        result = validate_uuid("AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA")
        assert result == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_uuid("not-a-uuid")

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_uuid("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa\x00aa")

    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            validate_uuid(12345)


class TestTitle:
    def test_valid(self):
        assert validate_title("My Report") == "My Report"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_title("")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_title("x" * 201)

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_title("title\x00evil")

    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            validate_title(42)

    def test_unicode_normalised(self):
        # NFC normalisation: combining character sequences
        import unicodedata
        nfd = "e\u0301"  # e + combining acute = é in NFD
        result = validate_title(nfd)
        assert unicodedata.is_normalized("NFC", result)


class TestSortCol:
    def test_valid_created_at(self):
        assert validate_sort_col("created_at") == SORT_COL_ALLOWLIST["created_at"]

    def test_valid_title(self):
        assert validate_sort_col("title") == SORT_COL_ALLOWLIST["title"]

    def test_none_returns_default(self):
        result = validate_sort_col(None)
        assert result in SORT_COL_ALLOWLIST.values()

    def test_injection_attempt_raises(self):
        with pytest.raises(ValidationError):
            validate_sort_col("created_at; DROP TABLE reports--")

    def test_unknown_column_raises(self):
        with pytest.raises(ValidationError):
            validate_sort_col("updated_at")

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_sort_col("created_at\x00")


class TestFilename:
    def test_valid(self):
        assert validate_filename("report.pdf") == "report.pdf"

    def test_path_traversal_slash_raises(self):
        with pytest.raises(ValidationError):
            validate_filename("../../etc/passwd")

    def test_path_traversal_backslash_raises(self):
        with pytest.raises(ValidationError):
            validate_filename("..\\windows\\system32")

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_filename("file\x00.pdf")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_filename("")

    def test_colon_raises(self):
        # Windows alternate data streams
        with pytest.raises(ValidationError):
            validate_filename("file:ads")


class TestContentType:
    def test_valid(self):
        assert validate_content_type("application/pdf") == "application/pdf"

    def test_strips_parameters(self):
        result = validate_content_type("text/plain; charset=utf-8")
        assert result == "text/plain"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_content_type("<script>")

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_content_type("text/plain\x00")


class TestSearchQuery:
    def test_valid(self):
        assert validate_search_query("quarterly") == "quarterly"

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_search_query("x" * 201)

    def test_nul_raises(self):
        with pytest.raises(ValidationError):
            validate_search_query("hello\x00world")
