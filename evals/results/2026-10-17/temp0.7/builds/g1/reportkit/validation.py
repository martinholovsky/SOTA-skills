"""
Input validation: allowlist-based, canonicalized before validation.
All validation happens at the trust boundary (handler layer).
"""

import re
import unicodedata
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TITLE_LEN = 200
MAX_BODY_LEN = 100_000
MAX_SEARCH_QUERY_LEN = 200
MAX_FILENAME_LEN = 255
MAX_CONTENT_TYPE_LEN = 128

# Allowlisted sort columns: map user-supplied token → SQL column name.
# Identifiers CANNOT be parameterized; this allowlist is the only safe path.
SORT_COL_ALLOWLIST: dict[str, str] = {
    "created_at": "r.created_at",
    "title": "r.title",
}
DEFAULT_SORT_COL = "created_at"

# Strict UUID pattern (lowercase hex, standard groups).
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Printable-ASCII-only content-type (RFC 7231 §3.1.1.1 media-type).
# We don't need to support exotic content types.
_CONTENT_TYPE_RE = re.compile(r"^[A-Za-z0-9!#$&\-^_]+/[A-Za-z0-9!#$&\-^_.+]+$")

# Safe filename: letters, digits, spaces, dots, hyphens, underscores.
# Stored for display only — never used as a filesystem path.
_FILENAME_RE = re.compile(r"^[\w\s.\-]{1,255}$", re.UNICODE)

# Bearer token: base64url characters (URL-safe base64, no padding required).
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-]{32,256}$")

# Billing event id: printable ASCII, no control chars.
_EVENT_ID_RE = re.compile(r"^[\x21-\x7E]{1,128}$")


class ValidationError(Exception):
    """Raised when input fails validation; message is safe to log (no PII)."""
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def _reject_nul(value: str, field: str) -> None:
    """NUL bytes are rejected in every field (C-string truncation risk)."""
    if "\x00" in value:
        raise ValidationError(field, "contains NUL byte")


def _nfc(value: str) -> str:
    """Canonicalize Unicode to NFC before any further validation."""
    return unicodedata.normalize("NFC", value)


def validate_uuid(value: Any, field: str = "id") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = value.strip().lower()
    _reject_nul(v, field)
    if not _UUID_RE.fullmatch(v):
        raise ValidationError(field, "not a valid UUID")
    return v


def validate_bearer_token(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("token", "must be a string")
    _reject_nul(value, "token")
    if not _TOKEN_RE.fullmatch(value):
        raise ValidationError("token", "invalid format")
    return value


def validate_title(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("title", "must be a string")
    v = _nfc(value.strip())
    _reject_nul(v, "title")
    if not v:
        raise ValidationError("title", "must not be empty")
    if len(v) > MAX_TITLE_LEN:
        raise ValidationError("title", f"exceeds {MAX_TITLE_LEN} characters")
    return v


def validate_body(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("body", "must be a string")
    v = _nfc(value)
    _reject_nul(v, "body")
    if len(v) > MAX_BODY_LEN:
        raise ValidationError("body", f"exceeds {MAX_BODY_LEN} characters")
    return v


def validate_search_query(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("q", "must be a string")
    v = _nfc(value.strip())
    _reject_nul(v, "q")
    if len(v) > MAX_SEARCH_QUERY_LEN:
        raise ValidationError("q", f"exceeds {MAX_SEARCH_QUERY_LEN} characters")
    return v


def validate_sort_col(value: Any) -> str:
    """
    Map user-supplied sort token to a safe SQL column expression.
    SQL identifiers cannot be parameterized; this allowlist is the boundary.
    Returns the literal SQL column expression (e.g. 'r.created_at').
    """
    if value is None:
        return SORT_COL_ALLOWLIST[DEFAULT_SORT_COL]
    if not isinstance(value, str):
        raise ValidationError("sort", "must be a string")
    _reject_nul(value, "sort")
    col = value.strip().lower()
    if col not in SORT_COL_ALLOWLIST:
        raise ValidationError(
            "sort",
            f"must be one of: {', '.join(SORT_COL_ALLOWLIST)}"
        )
    return SORT_COL_ALLOWLIST[col]


def validate_filename(value: Any) -> str:
    """Validate display-only filename. Never used as a filesystem path."""
    if not isinstance(value, str):
        raise ValidationError("filename", "must be a string")
    v = _nfc(value.strip())
    _reject_nul(v, "filename")
    if not v:
        raise ValidationError("filename", "must not be empty")
    if len(v) > MAX_FILENAME_LEN:
        raise ValidationError("filename", f"exceeds {MAX_FILENAME_LEN} characters")
    # Reject path separators — this is display metadata, but defense in depth.
    if "/" in v or "\\" in v or ":" in v:
        raise ValidationError("filename", "must not contain path characters")
    if not _FILENAME_RE.fullmatch(v):
        raise ValidationError("filename", "contains disallowed characters")
    return v


def validate_content_type(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("content_type", "must be a string")
    v = value.strip()
    _reject_nul(v, "content_type")
    if len(v) > MAX_CONTENT_TYPE_LEN:
        raise ValidationError("content_type", f"exceeds {MAX_CONTENT_TYPE_LEN} characters")
    # Strip parameters (e.g. "; charset=utf-8") before pattern check.
    base = v.split(";")[0].strip()
    if not _CONTENT_TYPE_RE.fullmatch(base):
        raise ValidationError("content_type", "invalid media type format")
    return base


def validate_event_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("event_id", "must be a string")
    _reject_nul(value, "event_id")
    if not _EVENT_ID_RE.fullmatch(value):
        raise ValidationError("event_id", "invalid event id format")
    return value


def validate_amount_cents(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("amount_cents", "must be an integer")
    if value < 0:
        raise ValidationError("amount_cents", "must be non-negative")
    if value > 10_000_000_00:  # $10M sanity cap
        raise ValidationError("amount_cents", "exceeds maximum")
    return value


def extract_bearer_token(request: dict) -> str:
    """
    Extract and validate the bearer token from Authorization header.
    Raises ValidationError if absent or malformed.
    """
    auth = request.get("headers", {}).get("Authorization", "")
    if not isinstance(auth, str) or not auth.startswith("Bearer "):
        raise ValidationError("Authorization", "missing or malformed Bearer token")
    return validate_bearer_token(auth[len("Bearer "):])
