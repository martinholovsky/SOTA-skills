"""
Attachment content scanning.

The scanner looks for a small set of disallowed byte-sequence markers.
Real deployments would call an external AV/content-policy service; this
implementation keeps everything in the standard library while preserving
the correct interface and error path.
"""

from .errors import ContentPolicyError

# Disallowed signatures: (label, byte_sequence)
_DISALLOWED: list[tuple[str, bytes]] = [
    ("EICAR test marker",  b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"),
    ("PE executable",      b"MZ\x90\x00"),          # DOS/PE header
    ("ELF executable",     b"\x7fELF"),
    ("Mach-O 64-bit",      b"\xcf\xfa\xed\xfe"),
    ("Mach-O 32-bit",      b"\xce\xfa\xed\xfe"),
]

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB


def scan(data: bytes, filename: str = "") -> None:
    """
    Raise ContentPolicyError if *data* contains a disallowed marker
    or exceeds the size limit.
    """
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ContentPolicyError(
            f"Attachment exceeds maximum size of {MAX_ATTACHMENT_BYTES} bytes."
        )

    for label, marker in _DISALLOWED:
        if marker in data:
            raise ContentPolicyError(
                f"Attachment rejected: disallowed content detected ({label})."
            )
