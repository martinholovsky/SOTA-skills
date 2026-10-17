"""Tests for the content scanner."""
import pytest
from reportkit.content_scanner import scan, DisallowedContentError


def test_clean_data_passes():
    scan(b"Hello, this is a plain text file.")


def test_eicar_rejected():
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    with pytest.raises(DisallowedContentError, match="eicar"):
        scan(eicar)


def test_pe_header_rejected():
    pe = b"MZ" + b"\x00" * 200
    with pytest.raises(DisallowedContentError, match="pe-executable"):
        scan(pe)


def test_elf_header_rejected():
    elf = b"\x7fELF" + b"\x00" * 100
    with pytest.raises(DisallowedContentError, match="elf-executable"):
        scan(elf)


def test_empty_bytes_passes():
    scan(b"")


def test_pdf_header_passes():
    # PDF starts with %PDF — not in disallowed list
    scan(b"%PDF-1.4 ..." + b"\x00" * 50)
