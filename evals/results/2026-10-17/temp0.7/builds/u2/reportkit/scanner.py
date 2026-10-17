"""Attachment content scanner.

Checks uploaded bytes for disallowed content markers before storage.
This is a structural placeholder: real deployments would shell out to
ClamAV, call a vendor API, or apply more sophisticated byte-pattern
matching.  The interface is intentionally narrow so it can be swapped.
"""

from .errors import DisallowedContentError

# Byte sequences that are unconditionally rejected.
# Extend this list or replace the function body with a real scanner.
_DISALLOWED_MARKERS: list[bytes] = [
    b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",   # EICAR test string
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",  # EICAR variant prefix
]

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB


def scan(data: bytes, filename: str = "") -> None:
    """Raise DisallowedContentError if *data* contains a disallowed marker.

    Raises AttachmentTooLargeError (a subclass of ValidationError) if the
    payload exceeds MAX_ATTACHMENT_BYTES.  Size is checked first so we never
    scan oversized blobs.
    """
    from .errors import AttachmentTooLargeError  # local to avoid circular

    if len(data) > MAX_ATTACHMENT_BYTES:
        raise AttachmentTooLargeError(
            f"Attachment '{filename}' exceeds the 25 MB limit "
            f"({len(data):,} bytes)"
        )

    for marker in _DISALLOWED_MARKERS:
        if marker in data:
            raise DisallowedContentError(
                f"Attachment '{filename}' contains disallowed content"
            )
