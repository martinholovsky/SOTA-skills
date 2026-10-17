"""Tests for the attachment content scanner."""

import pytest
from reportkit.content_scanner import scan, ContentViolation, MAX_ATTACHMENT_BYTES


class TestScan:
    def test_clean_data_passes(self):
        scan(b"hello world", "file.txt")  # no exception

    def test_eicar_string_rejected(self):
        with pytest.raises(ContentViolation):
            scan(b"prefix EICAR-STANDARD-ANTIVIRUS-TEST-FILE suffix", "bad.txt")

    def test_eicar_header_variant_rejected(self):
        with pytest.raises(ContentViolation):
            scan(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR", "bad2.txt")

    def test_oversized_raises_value_error(self):
        with pytest.raises(ValueError, match="25 MB"):
            scan(b"x" * (MAX_ATTACHMENT_BYTES + 1), "big.bin")

    def test_exactly_at_limit_passes(self):
        scan(b"x" * MAX_ATTACHMENT_BYTES, "ok.bin")  # no exception

    def test_empty_bytes_passes(self):
        scan(b"", "empty.txt")
