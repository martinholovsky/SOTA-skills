"""
Attachment content scanner.

Checks uploaded bytes for disallowed content markers before the attachment is
persisted.  The scanner is intentionally simple: it looks for a configurable
set of byte-string signatures.  In production this would delegate to a proper
AV/content-inspection service; the interface is kept stable so that swap-in is
straightforward.
"""

from __future__ import annotations

# Byte signatures that are unconditionally rejected.
# Extend this tuple to add new markers without changing call-sites.
_DISALLOWED_SIGNATURES: tuple[bytes, ...] = (
    b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",   # EICAR test string
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",  # EICAR header variant
)

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB


class ContentViolation(Exception):
    """Raised when a disallowed content marker is found in uploaded data."""


def scan(data: bytes, filename: str = "") -> None:
    """
    Scan *data* for disallowed content markers.

    Raises ContentViolation if any marker is found.
    Raises ValueError if the data exceeds the size limit.
    """
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachment {filename!r} exceeds the 25 MB limit "
            f"({len(data):,} bytes)."
        )
    for sig in _DISALLOWED_SIGNATURES:
        if sig in data:
            raise ContentViolation(
                f"Disallowed content marker detected in {filename!r}."
            )
