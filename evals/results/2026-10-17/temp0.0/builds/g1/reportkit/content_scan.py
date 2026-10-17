"""Attachment content scanning.

Checks for disallowed content markers (magic bytes for executable formats,
script shebangs, and a small set of known-bad signatures).

This is a defence-in-depth layer.  A production deployment should also route
attachments through a dedicated AV/malware-scanning service.
"""

from __future__ import annotations

# (offset, bytes) pairs that indicate disallowed content.
# Extend this list as new signatures are identified.
_DISALLOWED_SIGNATURES: list[tuple[int, bytes]] = [
    # Windows PE executable
    (0, b"MZ"),
    # ELF binary
    (0, b"\x7fELF"),
    # Mach-O 32-bit
    (0, b"\xfe\xed\xfa\xce"),
    # Mach-O 64-bit
    (0, b"\xfe\xed\xfa\xcf"),
    # Mach-O fat binary
    (0, b"\xca\xfe\xba\xbe"),
    # Script shebang
    (0, b"#!"),
    # Windows script host
    (0, b"<script"),
    # Java class file
    (0, b"\xca\xfe\xba\xbe"),
    # ZIP (could contain malicious content — flag for deeper inspection)
    # We allow ZIPs but mark them for manual review in a real system;
    # here we reject them outright as a conservative default.
    (0, b"PK\x03\x04"),
]

# Maximum bytes to read for signature checking
_SCAN_WINDOW = 256


def scan(data: bytes) -> tuple[bool, str]:
    """Return (is_clean, reason).

    *is_clean* is True when no disallowed signature is found.
    """
    window = data[:_SCAN_WINDOW]
    for offset, sig in _DISALLOWED_SIGNATURES:
        end = offset + len(sig)
        if window[offset:end] == sig:
            return False, f"disallowed content signature at offset {offset}"
    return True, "ok"
