"""
Input validation helpers.

All validation is allowlist-based, performed after any necessary
canonicalisation, and enforces length limits on every field.

No validation is done client-side; these functions are the single
authoritative layer.
"""

import re
import unicodedata
import uuid as _uuid_mod

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TITLE_LEN    = 200
MAX_BODY_LEN     = 100_000
MAX_SEARCH_LEN   = 200
MAX_FILENAME_LEN = 255
MAX_ATTACH_BYTES = 25 * 1024 * 1024   # 25 MiB

# Allowed sort columns (identifier allowlist — never interpolated raw).
SORT_COLUMN_MAP: dict[str, str] = {
    "created_at": "r.created_at",
    "title":      "r.title",
}

# Allowed content-types for attachments.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "text/plain",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

# Filename: printable ASCII letters, digits, dots, dashes, underscores.
# Rejects path separators, NUL, control characters, Windows reserved names.
_FILENAME_RE = re.compile(r'^[\w.\- ]{1,255}$', re.ASCII)

_WINDOWS_RESERVED = re.compile(
    r'^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\..*)?$', re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    """Raised when caller-supplied data fails validation."""
    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.field = field
        self.status = 400


# ---------------------------------------------------------------------------
# Primitive validators
# ---------------------------------------------------------------------------


def _reject_control(value: str, field: str) -> None:
    """Reject NUL and other ASCII control characters (except normal whitespace)."""
    for ch in value:
        cp = ord(ch)
        if cp == 0 or (cp < 0x20 and ch not in ("\t", "\n", "\r")):
            raise ValidationError(f"{field}: contains disallowed control character", field)


def require_string(value, field: str, *, max_len: int, min_len: int = 1) -> str:
    """
    Assert *value* is a non-empty string within [min_len, max_len] after
    NFC normalisation.  Rejects NUL and most control characters.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field}: must be a string", field)
    value = unicodedata.normalize("NFC", value)
    _reject_control(value, field)
    stripped = value.strip()
    if len(stripped) < min_len:
        raise ValidationError(f"{field}: must not be empty", field)
    if len(value) > max_len:
        raise ValidationError(
            f"{field}: exceeds maximum length of {max_len}", field
        )
    return value


def require_uuid(value, field: str) -> str:
    """Assert *value* is a valid UUID string and return its canonical form."""
    if not isinstance(value, str):
        raise ValidationError(f"{field}: must be a string", field)
    try:
        return str(_uuid_mod.UUID(value))
    except ValueError:
        raise ValidationError(f"{field}: must be a valid UUID", field)


def validate_sort_key(raw: str) -> str:
    """
    Map a user-supplied sort key to a safe SQL column expression.

    Uses a hard-coded allowlist dict; the raw value is never interpolated.
    Raises ValidationError for unknown keys.
    """
    col = SORT_COLUMN_MAP.get(raw)
    if col is None:
        raise ValidationError(
            f"sort: must be one of {sorted(SORT_COLUMN_MAP.keys())}",
            field="sort",
        )
    return col


def validate_filename(name: str) -> str:
    """
    Validate an attachment filename for display storage.

    The filename is NEVER used as a filesystem path — a server-generated
    UUID is used for storage.  We still validate it to prevent stored XSS
    and confusion.
    """
    name = unicodedata.normalize("NFC", name.strip())
    if not name:
        raise ValidationError("filename: must not be empty", "filename")
    if len(name) > MAX_FILENAME_LEN:
        raise ValidationError(
            f"filename: exceeds {MAX_FILENAME_LEN} characters", "filename"
        )
    if "\x00" in name or ":" in name or "/" in name or "\\" in name:
        raise ValidationError("filename: contains disallowed character", "filename")
    if _WINDOWS_RESERVED.match(name):
        raise ValidationError("filename: reserved name", "filename")
    if not _FILENAME_RE.match(name):
        raise ValidationError(
            "filename: only letters, digits, spaces, dots, dashes and underscores allowed",
            "filename",
        )
    return name


def validate_content_type(ct: str) -> str:
    """Validate attachment content-type against the allowlist."""
    # Strip parameters (e.g. "; charset=utf-8")
    base = ct.split(";")[0].strip().lower()
    if base not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"content_type: '{base}' is not permitted",
            "content_type",
        )
    return base


def validate_attachment_size(size: int) -> None:
    if not isinstance(size, int) or size <= 0:
        raise ValidationError("attachment: size must be a positive integer", "size")
    if size > MAX_ATTACH_BYTES:
        raise ValidationError(
            f"attachment: exceeds maximum size of {MAX_ATTACH_BYTES} bytes",
            "size",
        )
