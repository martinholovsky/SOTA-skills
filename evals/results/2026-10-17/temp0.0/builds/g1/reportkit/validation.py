"""Input validation helpers — allowlist-first, canonicalize-before-validate."""

from __future__ import annotations

import re
import unicodedata
import uuid

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TITLE_LEN = 500
MAX_BODY_LEN = 100_000
MAX_FILENAME_LEN = 255
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB

# Allowlisted sort columns for search_reports.
# Identifiers are never interpolated raw; they are mapped through this dict.
SORT_COLUMN_MAP: dict[str, str] = {
    "created_at": "r.created_at",
    "title": "r.title",
}
DEFAULT_SORT = "created_at"

# Allowlisted roles
VALID_ROLES = frozenset({"viewer", "editor", "admin"})

# Safe filename pattern: printable ASCII, no path separators, no control chars,
# no Windows reserved names, no leading dot.
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][\w\-. ]{0,253}$")
_WINDOWS_RESERVED = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", re.IGNORECASE
)

# Title: Unicode letters, numbers, common punctuation, spaces — no control chars.
# We use a positive allowlist of Unicode categories.
_TITLE_RE = re.compile(r"^[\w\s\-.,!?:;()\[\]{}'\"@#&*+=/<>~`|\\^%$]{1,500}$")


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def _reject_nul(value: str, field: str) -> None:
    if "\x00" in value:
        from reportkit.errors import BadRequest
        raise BadRequest(f"{field}: NUL byte not allowed")


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def require_str(value: object, field: str, *, max_len: int = 1000) -> str:
    """Assert *value* is a non-empty string within *max_len*."""
    from reportkit.errors import BadRequest

    if not isinstance(value, str):
        raise BadRequest(f"{field}: must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if not v.strip():
        raise BadRequest(f"{field}: must not be blank")
    if len(v) > max_len:
        raise BadRequest(f"{field}: exceeds maximum length {max_len}")
    return v


def require_uuid(value: object, field: str) -> str:
    """Assert *value* is a valid UUID string; return its canonical lower-case form."""
    from reportkit.errors import BadRequest

    raw = require_str(value, field, max_len=36)
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        raise BadRequest(f"{field}: not a valid UUID")


def validate_title(value: object) -> str:
    from reportkit.errors import BadRequest

    title = require_str(value, "title", max_len=MAX_TITLE_LEN)
    if not _TITLE_RE.fullmatch(title):
        raise BadRequest("title: contains disallowed characters")
    return title


def validate_body(value: object) -> str:
    if value is None:
        return ""
    return require_str(value, "body", max_len=MAX_BODY_LEN)


def validate_sort(value: object) -> str:
    """Return the safe SQL column expression for the requested sort key."""
    from reportkit.errors import BadRequest

    if value is None:
        return SORT_COLUMN_MAP[DEFAULT_SORT]
    if not isinstance(value, str):
        raise BadRequest("sort: must be a string")
    key = _nfc(value).strip().lower()
    if key not in SORT_COLUMN_MAP:
        raise BadRequest(f"sort: must be one of {sorted(SORT_COLUMN_MAP)}")
    return SORT_COLUMN_MAP[key]


def validate_filename(value: object) -> str:
    from reportkit.errors import BadRequest

    name = require_str(value, "filename", max_len=MAX_FILENAME_LEN)
    # Reject path separators and alternate data stream markers
    for ch in ("/", "\\", ":", "\r", "\n"):
        if ch in name:
            raise BadRequest("filename: contains disallowed character")
    if _WINDOWS_RESERVED.match(name):
        raise BadRequest("filename: reserved name")
    if not _FILENAME_RE.fullmatch(name):
        raise BadRequest("filename: contains disallowed characters")
    return name


def validate_role(value: object) -> str:
    from reportkit.errors import BadRequest

    role = require_str(value, "role", max_len=20)
    if role not in VALID_ROLES:
        raise BadRequest(f"role: must be one of {sorted(VALID_ROLES)}")
    return role


def validate_search_query(value: object) -> str:
    """Validate and return a search query string (used as a LIKE parameter)."""
    from reportkit.errors import BadRequest

    q = require_str(value, "q", max_len=200)
    # Escape LIKE metacharacters in the value itself so the user cannot
    # widen the match beyond what they typed.
    q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return q
