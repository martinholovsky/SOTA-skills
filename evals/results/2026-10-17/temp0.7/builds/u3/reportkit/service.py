"""ReportService — the HTTP surface of reportkit.

Each public method accepts a *request* dict and optional path parameters.
The request dict shape::

    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    <bytes | dict | None>,
        "query":   {"sort": "title", ...},   # parsed query string
    }

Methods return plain dicts; the HTTP adapter (not part of this package) is
responsible for serialising them and setting status codes.
"""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .auth import Caller, AuthError, PermissionError, bearer_token, resolve_caller
from .content_scanner import scan, DisallowedContentError
from . import events

_ALLOWED_SORT_COLUMNS = {"created_at", "title"}
_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


class ReportService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _authenticate(self, request: dict) -> Caller:
        token = bearer_token(request)
        return resolve_caller(self._conn, token)

    # ------------------------------------------------------------------
    # Report endpoints
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        caller = self._authenticate(request)
        caller.require("report:write")

        body: dict = request.get("body") or {}
        title = (body.get("title") or "").strip()
        content = body.get("body", "")

        if not title:
            return {"error": "title is required", "status": 400}

        report_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            """
            INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, caller.tenant_id, caller.user_id, title, content, now, now),
        )
        self._conn.commit()

        events.dispatch(
            "report.created",
            {
                "report_id": report_id,
                "tenant_id": caller.tenant_id,
                "owner_id":  caller.user_id,
            },
        )

        return {
            "status": 201,
            "report": {
                "id":         report_id,
                "tenant_id":  caller.tenant_id,
                "owner_id":   caller.user_id,
                "title":      title,
                "body":       content,
                "created_at": now,
                "updated_at": now,
            },
        }

    def get_report(self, request: dict, report_id: str) -> dict:
        caller = self._authenticate(request)
        caller.require("report:read")

        row = self._conn.execute(
            """
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports
            WHERE id = ? AND tenant_id = ?
            """,
            (report_id, caller.tenant_id),
        ).fetchone()

        if row is None:
            return {"error": "report not found", "status": 404}

        return {"status": 200, "report": _row_to_dict(row)}

    def list_reports(self, request: dict) -> dict:
        caller = self._authenticate(request)
        caller.require("report:read")

        rows = self._conn.execute(
            """
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports
            WHERE owner_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            """,
            (caller.user_id, caller.tenant_id),
        ).fetchall()

        return {"status": 200, "reports": [_row_to_dict(r) for r in rows]}

    def search_reports(self, request: dict) -> dict:
        caller = self._authenticate(request)
        caller.require("report:read")

        query_params: dict = request.get("query") or {}
        q = (query_params.get("q") or "").strip()

        # Validate sort column — user-supplied value, must be whitelisted before
        # interpolation into SQL to prevent injection.
        sort_raw = (query_params.get("sort") or "created_at").strip()
        if sort_raw not in _ALLOWED_SORT_COLUMNS:
            return {
                "error": f"sort must be one of {sorted(_ALLOWED_SORT_COLUMNS)}",
                "status": 400,
            }

        # SQLite LIKE is case-insensitive for ASCII; wrap the term in wildcards.
        like_term = f"%{q}%"

        # sort_raw is validated against the whitelist above so it is safe to
        # interpolate directly into the SQL string.
        sql = f"""
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports
            WHERE owner_id = ?
              AND tenant_id = ?
              AND title LIKE ?
            ORDER BY {sort_raw} ASC
        """
        rows = self._conn.execute(
            sql, (caller.user_id, caller.tenant_id, like_term)
        ).fetchall()

        return {"status": 200, "reports": [_row_to_dict(r) for r in rows]}

    def delete_report(self, request: dict, report_id: str) -> dict:
        caller = self._authenticate(request)
        caller.require("report:delete")

        row = self._conn.execute(
            "SELECT id, tenant_id FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, caller.tenant_id),
        ).fetchone()
        if row is None:
            return {"error": "report not found", "status": 404}

        self._conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self._conn.commit()

        events.dispatch(
            "report.deleted",
            {
                "report_id": report_id,
                "tenant_id": caller.tenant_id,
                "actor_id":  caller.user_id,
            },
        )

        return {"status": 200, "deleted": report_id}

    def upload_attachment(self, request: dict) -> dict:
        caller = self._authenticate(request)
        caller.require("report:write")

        body: dict = request.get("body") or {}
        report_id = (body.get("report_id") or "").strip()
        filename  = (body.get("filename")  or "attachment").strip()
        mime_type = (body.get("mime_type") or "application/octet-stream").strip()
        data: bytes = body.get("data") or b""

        if not report_id:
            return {"error": "report_id is required", "status": 400}

        if not isinstance(data, (bytes, bytearray)):
            return {"error": "data must be bytes", "status": 400}

        if len(data) > _MAX_ATTACHMENT_BYTES:
            return {
                "error": f"attachment exceeds maximum size of {_MAX_ATTACHMENT_BYTES} bytes",
                "status": 413,
            }

        # Verify the report belongs to this tenant
        report_row = self._conn.execute(
            "SELECT id FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, caller.tenant_id),
        ).fetchone()
        if report_row is None:
            return {"error": "report not found", "status": 404}

        # Content scan before storage
        try:
            scan(bytes(data))
        except DisallowedContentError as exc:
            return {"error": str(exc), "status": 422}

        attachment_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            """
            INSERT INTO attachments
                (id, report_id, tenant_id, filename, mime_type, size_bytes, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment_id,
                report_id,
                caller.tenant_id,
                filename,
                mime_type,
                len(data),
                data,
                now,
            ),
        )
        self._conn.commit()

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
