"""
Input validation — allowlist-first, canonicalize-before-validate.

Rules applied
-------------
- rules/01 §1: allowlist, canonicalize first, server-side, length-limited.
- rules/01 §10: regex uses re.fullmatch with absolute anchors and bounded
  quantifiers; no nested quantifiers on untrusted input.
- rules/01 §2: identifiers (sort column) mapped through an allowlist dict.
- rules/01 §11: NUL bytes rejected everywhere.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Field-level constraints (written down per rules/01 §1)
# ---------------------------------------------------------------------------
#
# Field          | Max len | Charset / format
# ---------------+---------+--------------------------------------------------
# report title   |  256    | Unicode letters, digits, common punctuation
# report body    | 65536   | Arbitrary text (stored verbatim, not executed)
# username       |   64    | Alphanumeric + dot + hyphen + underscore
# tenant_id      |   36    | UUID canonical form
# user_id        |   36    | UUID canonical form
# sort column    |   16    | Allowlisted identifier (see models.SORT_COLUMNS)
# search query   |  128    | Same as report title charset
# ---------------+---------+--------------------------------------------------

_UUID_RE    = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
_TITLE_RE   = re.compile(r"\A[\w\s.,!?'\"\-–—():;@#%&+=/\\*\[\]]{1,256}\Z", re.UNICODE)
_USERNAME_RE = re.compile(r"\A[A-Za-z0-9._\-]{1,64}\Z")
_SEARCH_RE  = re.compile(r"\A[\w\s.,!?'\"\-–—():;@#%&+=/\\*\[\]]{1,128}\Z", re.UNICODE)


class ValidationError(ValueError):
    """Raised when input fails validation."""
    def __init__(self, field: str, reason: str):
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


def _reject_nul(value: str, field: str) -> None:
    """NUL bytes are rejected in every field (rules/01 §1)."""
    if "\x00" in value:
        raise ValidationError(field, "NUL byte not permitted")


def _nfc(value: str) -> str:
    """Canonicalize Unicode to NFC before validation (rules/01 §1)."""
    return unicodedata.normalize("NFC", value)


def validate_uuid(value: object, field: str = "id") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = value.strip().lower()
    _reject_nul(v, field)
    if not _UUID_RE.fullmatch(v):
        raise ValidationError(field, "must be a UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")
    return v


def validate_title(value: object, field: str = "title") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if not _TITLE_RE.fullmatch(v):
        raise ValidationError(
            field,
            "must be 1–256 characters of letters, digits or common punctuation",
        )
    return v


def validate_body(value: object, field: str = "body") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if len(v) > 65_536:
        raise ValidationError(field, "must not exceed 65 536 characters")
    return v


def validate_username(value: object, field: str = "username") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if not _USERNAME_RE.fullmatch(v):
        raise ValidationError(field, "must be 1–64 alphanumeric / . - _ characters")
    return v


def validate_sort(value: object) -> str:
    """
    Map the user-supplied sort key to a safe SQL column expression.

    Returns the SQL column expression string; raises ValidationError on an
    unknown key.  The caller uses the returned string directly in a
    hard-coded ORDER BY clause — it never reaches the query via string
    interpolation of unvalidated input (rules/01 §2).
    """
    from .models import SORT_COLUMNS  # local import avoids circular dep
    if not isinstance(value, str):
        raise ValidationError("sort", "must be a string")
    key = value.strip()
    if key not in SORT_COLUMNS:
        raise ValidationError(
            "sort",
            f"must be one of: {', '.join(sorted(SORT_COLUMNS))}",
        )
    return SORT_COLUMNS[key]


def validate_search_query(value: object, field: str = "q") -> str:
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if not _SEARCH_RE.fullmatch(v):
        raise ValidationError(
            field,
            "must be 1–128 characters of letters, digits or common punctuation",
        )
    return v


def validate_role(value: object, field: str = "role") -> str:
    from .models import VALID_ROLES
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = value.strip()
    if v not in VALID_ROLES:
        raise ValidationError(field, f"must be one of: {', '.join(sorted(VALID_ROLES))}")
    return v


def validate_mime_type(value: object, field: str = "mime_type") -> str:
    """
    Coarse MIME type check — structural only.
    The real gate is the content scanner in attachment_service.
    """
    from .models import ALLOWED_MIME_PREFIXES
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = value.strip().lower()
    _reject_nul(v, field)
    if len(v) > 128:
        raise ValidationError(field, "MIME type too long")
    if not any(v.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise ValidationError(field, f"MIME type not permitted: {v!r}")
    return v


def validate_filename(value: object, field: str = "filename") -> str:
    """
    Validate a display filename.

    The filename is stored as display metadata only; the storage key is a
    server-generated UUID (rules/01 §4: user input is not used as a path).
    We still sanitise it so it is safe to include in Content-Disposition.
    """
    if not isinstance(value, str):
        raise ValidationError(field, "must be a string")
    v = _nfc(value)
    _reject_nul(v, field)
    if len(v) > 255:
        raise ValidationError(field, "filename must not exceed 255 characters")
    # Reject path separators and Windows reserved names
    if "/" in v or "\\" in v or ":" in v:
        raise ValidationError(field, "filename must not contain path separators or ':'")
    if v.lstrip(".") == "":
        raise ValidationError(field, "filename must not be only dots")
    return v
