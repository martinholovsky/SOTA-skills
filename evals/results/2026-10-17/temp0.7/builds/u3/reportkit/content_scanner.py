"""Attachment content scanner.

Checks uploaded bytes for disallowed content markers before storage.
This is intentionally simple: real deployments should replace or augment
this with a proper AV / DLP integration.
"""

# Byte-string signatures for disallowed content.
# Each entry is (label, magic_bytes).
_DISALLOWED_SIGNATURES: list[tuple[str, bytes]] = [
    # EICAR anti-malware test string
    ("eicar-test", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"),
    # Windows PE executable
    ("pe-executable", b"MZ"),
    # ELF executable
    ("elf-executable", b"\x7fELF"),
]

# Maximum bytes to inspect (avoids scanning entire 25 MB for header sigs)
_SCAN_WINDOW = 512


class DisallowedContentError(Exception):
    """Raised when a disallowed content marker is found."""


def scan(data: bytes) -> None:
    """Raise DisallowedContentError if *data* contains a disallowed marker.

    Only the leading _SCAN_WINDOW bytes are checked for magic-byte signatures;
    the EICAR string can appear anywhere so the full buffer is searched for it.
    """
    header = data[:_SCAN_WINDOW]
    for label, sig in _DISALLOWED_SIGNATURES:
        haystack = data if label == "eicar-test" else header
        if sig in haystack:
            raise DisallowedContentError(
                f"Attachment rejected: disallowed content marker '{label}'"
            )
