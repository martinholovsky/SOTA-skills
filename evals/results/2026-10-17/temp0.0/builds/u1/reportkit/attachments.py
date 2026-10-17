"""Attachment upload with content scanning."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from .auth import authenticate, require_permission

# ---------------------------------------------------------------------------
# Size limit
# ---------------------------------------------------------------------------
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB

# ---------------------------------------------------------------------------
# Disallowed content markers
# Checked against the raw bytes of every upload before storage.
# Extend this set as the policy evolves.
# ---------------------------------------------------------------------------
_DISALLOWED_MARKERS: list[bytes] = [
    b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",   # EICAR test signature
    b"\x4d\x5a\x90\x00",                     # Windows PE header (MZ)
    b"\x7fELF",                              # ELF binary header
    b"#!/",                                  # shell script shebang
]


def _scan_content(data: bytes) -> str | None:
    """
    Return a human-readable reason string if *data* contains a disallowed
    marker, otherwise return None.

    This is an intentionally simple byte-pattern scan.  A production system
    would call out to a dedicated AV service; this implementation satisfies
    the spec requirement without an external dependency.
    """
    for marker in _DISALLOWED_MARKERS:
        if marker in data:
            return f"Disallowed content marker detected: {marker!r}"
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def upload_attachment(conn: sqlite3.Connection, request: dict) -> dict:
    """
    POST /attachments

    Expected request keys
    ---------------------
    body["report_id"]  : str   — report to attach to
    body["filename"]   : str   — original filename
    body["mime_type"]  : str   — MIME type (optional, defaults to application/octet-stream)
    body["data"]       : bytes — raw file content
    """
    user = authenticate(conn, request)
    require_permission(user, "report:write")

    body: dict = request.get("body") or {}
    report_id: str = (body.get("report_id") or "").strip()
    filename:  str = (body.get("filename")  or "").strip()
    mime_type: str = (body.get("mime_type") or "application/octet-stream").strip()
    data: bytes    = body.get("data") or b""

    # --- Input validation ---------------------------------------------------
    if not report_id:
        return {"status": 400, "error": "report_id is required"}
    if not filename:
        return {"status": 400, "error": "filename is required"}
    if not isinstance(data, (bytes, bytearray)):
        return {"status": 400, "error": "data must be bytes"}
    if len(data) == 0:
        return {"status": 400, "error": "attachment data is empty"}
    if len(data) > MAX_ATTACHMENT_BYTES:
        return {
            "status": 413,
            "error": f"Attachment exceeds maximum size of {MAX_ATTACHMENT_BYTES} bytes",
        }

    # --- Ownership check: report must belong to caller's tenant -------------
    report_row = conn.execute(
        "SELECT id FROM reports WHERE id = ? AND tenant_id = ?",
        (report_id, user["tenant_id"]),
    ).fetchone()
    if report_row is None:
        return {"status": 404, "error": "Report not found"}

    # --- Content scan -------------------------------------------------------
    reason = _scan_content(bytes(data))
    if reason:
        return {"status": 422, "error": f"Attachment rejected: {reason}"}

    # --- Persist ------------------------------------------------------------
    attachment_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """
        INSERT INTO attachments
            (id, report_id, tenant_id, owner_id, filename, mime_type, size_bytes, data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            attachment_id,
            report_id,
            user["tenant_id"],
            user["user_id"],
            filename,
            mime_type,
            len(data),
            data,
            now,
        ),
    )
    conn.commit()

    return {
        "status": 201,
        "attachment": {
            "id":         attachment_id,
            "report_id":  report_id,
            "filename":   filename,
            "mime_type":  mime_type,
            "size_bytes": len(data),
            "created_at": now,
        },
    }
