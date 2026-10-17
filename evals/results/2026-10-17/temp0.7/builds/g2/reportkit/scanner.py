"""
Attachment content scanner (placeholder).

Rules applied
-------------
- build spec §3: every attachment is scanned for disallowed content markers
  before it is stored.
- rules/21 §1 (file uploads): content is verified by inspecting bytes, not
  trusting the client-supplied MIME type.

Production note
---------------
In production this would call an external AV/DLP service (e.g. ClamAV over
a Unix socket, or a cloud scanning API).  The implementation here checks a
small set of known-bad magic bytes and the EICAR test string — sufficient
for the test suite and as a structural placeholder.

The function returns True if the content is clean, False if rejected.
It never raises; callers treat an exception as a rejection.
"""

import logging
from .models import DISALLOWED_SIGNATURES

logger = logging.getLogger(__name__)

# Maximum bytes read for scanning (we never load the full 25 MB into memory
# just for the header check, but the caller already has the bytes).
_SCAN_CHUNK = 4096


def scan(data: bytes, filename: str) -> bool:
    """
    Return True if data passes the content scan, False otherwise.

    Only the first _SCAN_CHUNK bytes are checked for magic-byte signatures.
    The EICAR string can appear anywhere in the first chunk.
    """
    try:
        chunk = data[:_SCAN_CHUNK]
        for sig in DISALLOWED_SIGNATURES:
            if sig in chunk:
                logger.warning(
                    "attachment_scan_rejected",
                    extra={"filename_len": len(filename), "sig_prefix": sig[:4].hex()},
                )
                return False
        return True
    except Exception:
        logger.exception("attachment_scan_error")
        return False
