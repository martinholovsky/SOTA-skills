"""Tests for the content scanner."""

import pytest

from reportkit.content_scan import MAX_ATTACHMENT_BYTES, ContentViolation, scan


class TestContentScan:
    def test_clean_text(self):
        scan(b"Hello, this is a normal text file.", filename="readme.txt")

    def test_clean_binary(self):
        scan(bytes(range(256)) * 10, filename="data.bin")

    def test_eicar_rejected(self):
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        with pytest.raises(ContentViolation) as exc_info:
            scan(eicar, filename="eicar.com")
        assert exc_info.value.label == "EICAR-TEST"

    def test_elf_rejected(self):
        with pytest.raises(ContentViolation) as exc_info:
            scan(b"\x7fELF" + b"\x00" * 100)
        assert exc_info.value.label == "ELF"

    def test_php_rejected(self):
        with pytest.raises(ContentViolation) as exc_info:
            scan(b"<?php echo 'hello'; ?>")
        assert exc_info.value.label == "PHP-TAG"

    def test_oversized_rejected(self):
        with pytest.raises(ValueError, match="maximum size"):
            scan(b"A" * (MAX_ATTACHMENT_BYTES + 1))

    def test_exactly_at_limit_ok(self):
        # Should not raise (boundary condition)
        scan(b"A" * MAX_ATTACHMENT_BYTES)
