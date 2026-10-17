"""
Attachment content scanner.

Checks for disallowed content markers before an attachment is stored.
This is a structural placeholder: real deployments would call an AV/DLP
service.  The interface is kept synchronous and the result is a bool so
callers can swap in an async or RPC implementation without changing the
handler.

Disallowed markers checked here:
- EICAR test string (standard AV test vector).
- A configurable list of byte-sequence signatures.

See NOTES.md for the production integration note.
"""

import logging

logger = logging.getLogger(__name__)

# EICAR standard test file (first 68 bytes).
_EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

# Additional disallowed byte signatures can be added here.
_DISALLOWED_SIGNATURES: list[bytes] = [
    _EICAR,
]


def is_clean(data: bytes) -> bool:
    """
    Return True if the content passes all checks.
    Logs a warning (no PII, no content) if a match is found.
    """
    for sig in _DISALLOWED_SIGNATURES:
        if sig in data:
            logger.warning(
                "attachment_scan_rejected sig_len=%d content_len=%d",
                len(sig),
                len(data),
            )
            return False
    return True
