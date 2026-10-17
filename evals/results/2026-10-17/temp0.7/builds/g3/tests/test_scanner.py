"""Tests for the attachment content scanner."""

from reportkit.scanner import scan


def test_clean_pdf():
    data = b"%PDF-1.4 some content here" + b"\x00" * 100
    result = scan(data)
    assert result.clean


def test_eicar_flagged():
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}" + b"}" * 50
    result = scan(eicar)
    assert not result.clean
    assert "EICAR" in result.reason


def test_pe_executable_flagged():
    result = scan(b"MZ" + b"\x00" * 200)
    assert not result.clean


def test_elf_flagged():
    result = scan(b"\x7fELF" + b"\x00" * 100)
    assert not result.clean


def test_php_flagged():
    result = scan(b"<?php echo 'hello'; ?>")
    assert not result.clean


def test_shell_script_flagged():
    result = scan(b"#!/bin/bash\necho hello")
    assert not result.clean


def test_empty_bytes_clean():
    result = scan(b"")
    assert result.clean
