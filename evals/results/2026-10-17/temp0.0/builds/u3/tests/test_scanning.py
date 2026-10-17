"""Tests for the attachment content scanner."""

import pytest

from reportkit.errors import ContentPolicyError
from reportkit.scanning import MAX_ATTACHMENT_BYTES, scan


class TestScan:
    def test_clean_data_passes(self):
        scan(b"Hello, world!", "hello.txt")  # no exception

    def test_empty_data_passes(self):
        scan(b"", "empty.bin")

    def test_eicar_rejected(self):
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        with pytest.raises(ContentPolicyError, match="EICAR"):
            scan(eicar, "eicar.com")

    def test_pe_header_rejected(self):
        pe = b"MZ\x90\x00" + b"\x00" * 100
        with pytest.raises(ContentPolicyError, match="PE"):
            scan(pe, "malware.exe")

    def test_elf_header_rejected(self):
        elf = b"\x7fELF" + b"\x00" * 100
        with pytest.raises(ContentPolicyError, match="ELF"):
            scan(elf, "binary")

    def test_oversized_rejected(self):
        big = b"A" * (MAX_ATTACHMENT_BYTES + 1)
        with pytest.raises(ContentPolicyError, match="size"):
            scan(big)

    def test_exactly_max_size_passes(self):
        data = b"B" * MAX_ATTACHMENT_BYTES
        scan(data, "big.bin")  # no exception

    def test_marker_embedded_in_larger_payload(self):
        payload = b"some prefix " + b"\x7fELF" + b" some suffix"
        with pytest.raises(ContentPolicyError):
            scan(payload, "sneaky.bin")
