"""
Domain constants and lightweight value objects.

No ORM — all persistence is through explicit parameterised queries in
the service layer, keeping the boundary between data and code visible.
"""

# ---------------------------------------------------------------------------
# Role → permission mapping (single source of truth)
# rules/03 §3: permissions derived server-side from role, never from request.
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "viewer": [
        "report:read",
    ],
    "editor": [
        "report:read",
        "report:write",
    ],
    "admin": [
        "report:read",
        "report:write",
        "report:delete",
        "user:manage",
    ],
}

VALID_ROLES = frozenset(ROLE_PERMISSIONS.keys())

# ---------------------------------------------------------------------------
# Attachment limits
# ---------------------------------------------------------------------------

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024   # 25 MB

# Coarse MIME allowlist — the scanner is the real gate; this is a first-pass
# structural check so obviously wrong content types are rejected early.
ALLOWED_MIME_PREFIXES = (
    "image/",
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats",   # .xlsx, .docx, .pptx
    "application/vnd.ms-",              # legacy Office
    "application/zip",
    "application/octet-stream",
)

# ---------------------------------------------------------------------------
# Sort-column allowlist (rules/01 §2: identifiers mapped through allowlist)
# ---------------------------------------------------------------------------

SORT_COLUMNS: dict[str, str] = {
    "created_at": "r.created_at",
    "title":      "r.title",
}

# ---------------------------------------------------------------------------
# Disallowed content markers (attachment scanning)
# These are byte-string signatures; real production code would call an
# external AV service.  The scanner here is a placeholder that checks for
# a small set of known-bad magic bytes and the EICAR test string.
# ---------------------------------------------------------------------------

DISALLOWED_SIGNATURES: list[bytes] = [
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",   # EICAR test file
    b"\x4d\x5a\x90\x00",                        # MZ PE header (Windows executable)
    b"\x7fELF",                                  # ELF executable
]
