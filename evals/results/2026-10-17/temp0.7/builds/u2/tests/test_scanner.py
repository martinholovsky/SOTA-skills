"""Tests for the attachment content scanner."""

import pytest
from reportkit.scanner import scan, MAX_ATTACHMENT_BYTES
from reportkit.errors import DisallowedContentError, AttachmentTooLargeError


def test_clean_file_passes():
    scan(b"hello, world", "hello.txt")  # should not raise


def test_eicar_rejected():
    with pytest.raises(DisallowedContentError):
        scan(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", "test.txt")


def test_oversized_rejected():
    big = b"a" * (MAX_ATTACHMENT_BYTES + 1)
    with pytest.raises(AttachmentTooLargeError):
        scan(big, "big.bin")


def test_exactly_max_size_passes():
    ok = b"a" * MAX_ATTACHMENT_BYTES
    scan(ok, "max.bin")  # should not raise


def test_empty_file_passes():
    scan(b"", "empty.txt")
