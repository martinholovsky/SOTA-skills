"""
Input validation helpers.

All validation is allowlist-based, performed after any decoding,
server-side (rules/01 §1).
"""

import re
import unicodedata
from typing import Any

from .errors import BadRequest

# ---------------------------------------------------------------------------
# Field-level validators
# ---------------------------------------------------------------------------

# Printable Unicode text: letters, numbers, common punctuation, spaces.
# Rejects NUL, control characters, and surrogate code points.
_SAFE_TEXT_RE = re.compile(
    r"^[\u0020-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]{1,500}$"
)

# Title: 1–500 printable characters, no NUL.
_TITLE_RE = re.compile(
    r"^[\u0020-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]{1,500}$"
)

# Filename: printable ASCII only, no path separators, no NUL, no control chars.
# Allowlist: letters, digits, hyphen, underscore, dot, space.
_FILENAME_RE = re.compile(r"^[A-Za-z0-9 ._\-]{1,255}$")

# UUID v4 pattern.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Allowed sort keys — validated against the DB allowlist in db.py too.
_ALLOWED_SORT_KEYS = frozenset({"created_at", "title"})

# Allowed MIME type pattern (type/subtype, no parameters).
_MIME_RE = re.compile(r"^[a-z0-9][a-z0-9!#$&\-^_]{0,126}/[a-z0-9][a-z0-9!#$&\-^_.+]{0,126}$")


def require_string(value: Any, field: str, min_len: int = 1, max_len: int = 500) -> str:
    """Assert *value* is a non-empty string within length bounds."""
    if not isinstance(value, str):
        raise BadRequest(f"'{field}' must be a string")
    # Canonicalize: NFC normalization before validation (rules/01 §1).
    value = unicodedata.normalize("NFC", value)
    if "\x00" in value:
        raise BadRequest(f"'{field}' must not contain NUL bytes")
    if not (min_len <= len(value) <= max_len):
        raise BadRequest(
            f"'{field}' must be between {min_len} and {max_len} characters"
        )
    return value


def require_title(value: Any) -> str:
    s = require_string(value, "title", 1, 500)
    if not _TITLE_RE.fullmatch(s):
        raise BadRequest("'title' contains disallowed characters")
    return s


def require_body(value: Any) -> str:
    """Body may be empty but must be a string and ≤ 1 MiB."""
    if not isinstance(value, str):
        raise BadRequest("'body' must be a string")
    value = unicodedata.normalize("NFC", value)
    if "\x00" in value:
        raise BadRequest("'body' must not contain NUL bytes")
    if len(value) > 1_048_576:
        raise BadRequest("'body' exceeds 1 MiB limit")
    return value


def require_uuid(value: Any, field: str = "id") -> str:
    if not isinstance(value, str):
        raise BadRequest(f"'{field}' must be a string")
    value = value.strip().lower()
    if not _UUID_RE.fullmatch(value):
        raise BadRequest(f"'{field}' is not a valid UUID")
    return value


def require_sort_key(value: Any) -> str:
    """Validate a user-supplied sort key against the allowlist."""
    if not isinstance(value, str):
        raise BadRequest("'sort' must be a string")
    value = value.strip().lower()
    if value not in _ALLOWED_SORT_KEYS:
        raise BadRequest(
            f"'sort' must be one of: {', '.join(sorted(_ALLOWED_SORT_KEYS))}"
        )
    return value


def require_filename(value: Any) -> str:
    if not isinstance(value, str):
        raise BadRequest("'filename' must be a string")
    value = unicodedata.normalize("NFC", value)
    if "\x00" in value:
        raise BadRequest("'filename' must not contain NUL bytes")
    # Reject path traversal components.
    if ".." in value or "/" in value or "\\" in value or ":" in value:
        raise BadRequest("'filename' must not contain path separators or colons")
    if not _FILENAME_RE.fullmatch(value):
        raise BadRequest(
            "'filename' must contain only letters, digits, spaces, "
            "hyphens, underscores, and dots"
        )
    return value


def require_mime_type(value: Any) -> str:
    if not isinstance(value, str):
        raise BadRequest("'content_type' must be a string")
    value = value.strip().lower()
    if not _MIME_RE.fullmatch(value):
        raise BadRequest("'content_type' is not a valid MIME type")
    return value


def require_bytes(value: Any, field: str, max_bytes: int) -> bytes:
    if not isinstance(value, (bytes, bytearray)):
        raise BadRequest(f"'{field}' must be bytes")
    if len(value) > max_bytes:
        raise BadRequest(
            f"'{field}' exceeds maximum size of {max_bytes} bytes"
        )
    return bytes(value)


def extract_bearer_token(request: dict) -> str:
    """
    Extract the bearer token from request["headers"]["Authorization"].

    Raises Unauthorized (via the caller) if absent or malformed.
    """
    from .errors import Unauthorized

    headers = request.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if not isinstance(auth, str):
        raise Unauthorized("Authorization header must be a string")
    auth = auth.strip()
    if not auth.lower().startswith("bearer "):
        raise Unauthorized("Authorization header must use Bearer scheme")
    token = auth[7:].strip()
    if not token:
        raise Unauthorized("Bearer token is empty")
    return token
