"""
Attachment content scanner.

Checks uploaded bytes for disallowed content markers before storage.
This is intentionally a simple magic-byte / pattern scanner; a real
deployment would call an external AV service.  The interface is kept
narrow so it can be swapped without touching the service layer.
"""

# Disallowed magic-byte signatures (offset, bytes).
# Extend this list as new threats are identified.
_SIGNATURES: list[tuple[int, bytes, str]] = [
    # EICAR test string (anti-malware test file)
    (0, b"X5O!P%@AP[4\\PZX54(P^)7CC)7}", "EICAR test file"),
    # Windows PE executable
    (0, b"MZ", "Windows PE executable"),
    # ELF executable
    (0, b"\x7fELF", "ELF executable"),
    # PHP open tag
    (0, b"<?php", "PHP script"),
    # Shell script
    (0, b"#!/", "shell script"),
]

# Maximum bytes we read for scanning (we don't need to read the whole file
# for magic-byte checks, but we do need enough for pattern matching).
_SCAN_WINDOW = 1024


class ScanResult:
    __slots__ = ("clean", "reason")

    def __init__(self, clean: bool, reason: str = "") -> None:
        self.clean  = clean
        self.reason = reason


def scan(data: bytes) -> ScanResult:
    """
    Scan *data* for disallowed content markers.

    Returns a ScanResult.  The caller decides whether to reject or store
    based on `result.clean`.
    """
    window = data[:_SCAN_WINDOW]
    for offset, signature, label in _SIGNATURES:
        if window[offset : offset + len(signature)] == signature:
            return ScanResult(clean=False, reason=label)
    return ScanResult(clean=True)
