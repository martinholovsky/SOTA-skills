"""
Attachment content scanning.

Checks uploaded bytes for disallowed content markers before the attachment is
persisted.  The implementation uses a simple byte-pattern registry so that new
signatures can be added without touching the upload logic.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Disallowed byte signatures
# Each entry is (label, bytes_to_search_for).
# ---------------------------------------------------------------------------

_SIGNATURES: list[tuple[str, bytes]] = [
    # EICAR anti-malware test string
    ("EICAR-TEST", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"),
    # Executable magic bytes (MZ header — Windows PE)
    ("EXE-MZ", b"MZ"),
    # ELF magic bytes
    ("ELF", b"\x7fELF"),
    # PHP open tag
    ("PHP-TAG", b"<?php"),
    # JSP/servlet marker
    ("JSP-TAG", b"<%@"),
]

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB


class ContentViolation(Exception):
    """Raised when a disallowed content marker is found."""

    def __init__(self, label: str) -> None:
        super().__init__(f"Disallowed content detected: {label}")
        self.label = label


def scan(data: bytes, filename: str = "") -> None:
    """
    Scan *data* for disallowed content markers.

    Raises :class:`ContentViolation` on the first match found.
    Raises :class:`ValueError` if the data exceeds the size limit.
    """
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachment exceeds maximum size of {MAX_ATTACHMENT_BYTES} bytes "
            f"(got {len(data)} bytes)."
        )

    # Only scan the first 4 KB for magic bytes to keep things fast on large
    # files; the EICAR string is always near the start.
    head = data[:4096]

    for label, signature in _SIGNATURES:
        if signature in head:
            logger.warning("Content scan failed for '%s': %s", filename, label)
            raise ContentViolation(label)
