"""
Attachment content scanner.

Checks uploaded bytes for disallowed content markers before storage.
In production this would delegate to a real AV/DLP library; the
interface is stable so the implementation can be swapped.
"""

from .config import Config
from .logging import get_logger

logger = get_logger(__name__)


def scan(data: bytes, filename: str) -> tuple[bool, str]:
    """
    Scan *data* for disallowed content.

    Returns (is_clean: bool, reason: str).
    reason is empty when is_clean is True.
    """
    for marker in Config.DISALLOWED_CONTENT_MARKERS:
        if marker in data:
            logger.warning(
                "attachment_scan_rejected",
                extra={"filename": filename, "marker_prefix": marker[:8].hex()},
            )
            return False, "disallowed content detected"

    logger.info(
        "attachment_scan_clean",
        extra={"filename": filename, "size": len(data)},
    )
    return True, ""
