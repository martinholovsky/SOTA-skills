"""
HTTP surface for reportkit.

All public methods accept a *request* dict modelled after a minimal WSGI/ASGI
envelope:

    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    <bytes | dict>,          # dict for JSON, bytes for binary
        "query":   {"sort": "title", ...},  # URL query parameters
    }

Methods return a response dict:

    {"status": <int>, "body": <JSON-serialisable dict>}

No web framework is used; the class can be driven directly in tests or wrapped
by any WSGI/ASGI adapter.
"""

from __future__ import annotations

import sqlite3
import uuid
import logging

from reportkit.auth import (
    AuthenticationError,
    AuthorizationError,
    resolve_caller,
    require_permission,
)
from reportkit.content_scanner import scan, ContentViolation
from reportkit.db import validate_sort_column
from reportkit import events

logger = logging.getLogger(__name__)

_DEFAULT_SORT = "created_at"


def _ok(body: dict, status: int = 200) -> dict:
    return {"status": status, "body": body}


def _err(message: str, status: int) -> dict:
    return {"status": status, "body": {"error": message}}


class ReportHandlers:
    """
    HTTP surface for the report service.

    Instantiate once per process (or per test) with a live database connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _authenticate(self, request: dict) -> dict:
        """Resolve caller or raise AuthenticationError / AuthorizationError."""
        return resolve_caller(self._conn, request)

    def _get_report_row(self, report_id: str, caller: dict):
        return self._conn.execute(
            "SELECT * FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, caller["tenant_id"]),
        ).fetchone()

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """POST /reports — create a report for the authenticated caller."""
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:write")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        body = request.get("body") or {}
        title = (body.get("title") or "").strip()
        content = (body.get("body") or "").strip()

        if not title:
            return _err("'title' is required.", 400)

        report_id = str(uuid.uuid4())
        try:
            self._conn.execute(
                """
                INSERT INTO reports (id, tenant_id, owner_id, title, body)
                VALUES (?, ?, ?, ?, ?)
                """,
                (report_id, caller["tenant_id"], caller["user_id"], title, content),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.exception("create_report db error")
            return _err(f"Database error: {exc}", 500)

        events.dispatch(
            "report.created",
            {
                "report_id": report_id,
                "tenant_id": caller["tenant_id"],
                "owner_id":  caller["user_id"],
            },
        )

        row = self._get_report_row(report_id, caller)
        return _ok(dict(row), 201)

    def get_report(self, request: dict, report_id: str) -> dict:
        """GET /reports/<id> — return a single report."""
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:read")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        row = self._get_report_row(report_id, caller)
        if row is None:
            return _err("Report not found.", 404)

        return _ok(dict(row))

    def list_reports(self, request: dict) -> dict:
        """GET /reports — list the caller's own reports, newest first."""
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:read")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        rows = self._conn.execute(
            """
            SELECT * FROM reports
            WHERE owner_id  = ?
              AND tenant_id = ?
            ORDER BY created_at DESC
            """,
            (caller["user_id"], caller["tenant_id"]),
        ).fetchall()

        return _ok({"reports": [dict(r) for r in rows]})

    def search_reports(self, request: dict) -> dict:
        """
        GET /reports/search?q=<term>&sort=<created_at|title>

        Title search across the caller's own reports.  The sort column is
        validated against an allowlist before interpolation into SQL.
        """
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:read")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        query_params = request.get("query") or {}
        search_term  = (query_params.get("q") or "").strip()
        sort_raw     = (query_params.get("sort") or _DEFAULT_SORT).strip()

        try:
            sort_col = validate_sort_column(sort_raw)
        except ValueError as exc:
            return _err(str(exc), 400)

        like_pattern = f"%{search_term}%"

        # sort_col is safe: validated against a frozenset allowlist.
        sql = f"""
            SELECT * FROM reports
            WHERE owner_id  = ?
              AND tenant_id = ?
              AND title LIKE ?
            ORDER BY {sort_col} ASC
        """
        rows = self._conn.execute(
            sql,
            (caller["user_id"], caller["tenant_id"], like_pattern),
        ).fetchall()

        return _ok({"reports": [dict(r) for r in rows]})

    def delete_report(self, request: dict, report_id: str) -> dict:
        """DELETE /reports/<id> — delete a report."""
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:delete")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        row = self._get_report_row(report_id, caller)
        if row is None:
            return _err("Report not found.", 404)

        try:
            self._conn.execute(
                "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
                (report_id, caller["tenant_id"]),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.exception("delete_report db error")
            return _err(f"Database error: {exc}", 500)

        events.dispatch(
            "report.deleted",
            {
                "report_id": report_id,
                "tenant_id": caller["tenant_id"],
                "actor_id":  caller["user_id"],
            },
        )

        return _ok({"deleted": report_id})

    def upload_attachment(self, request: dict) -> dict:
        """
        POST /attachments

        Expects request["body"] to be a dict:
            {
                "report_id": str,
                "filename":  str,
                "mime_type": str,          # optional
                "data":      bytes,
            }

        The attachment is scanned for disallowed content before storage.
        """
        try:
            caller = self._authenticate(request)
        except (AuthenticationError, AuthorizationError) as exc:
            return _err(str(exc), 401)

        try:
            require_permission(caller, "report:write")
        except AuthorizationError as exc:
            return _err(str(exc), 403)

        body      = request.get("body") or {}
        report_id = (body.get("report_id") or "").strip()
        filename  = (body.get("filename")  or "").strip()
        mime_type = (body.get("mime_type") or "application/octet-stream").strip()
        data: bytes = body.get("data") or b""

        if not report_id:
            return _err("'report_id' is required.", 400)
        if not filename:
            return _err("'filename' is required.", 400)
        if not isinstance(data, (bytes, bytearray)):
            return _err("'data' must be bytes.", 400)

        # Verify the report exists and belongs to this tenant.
        report_row = self._get_report_row(report_id, caller)
        if report_row is None:
            return _err("Report not found.", 404)

        # Content scan before persistence.
        try:
            scan(bytes(data), filename)
        except ValueError as exc:
            return _err(str(exc), 413)
        except ContentViolation as exc:
            return _err(str(exc), 422)

        attachment_id = str(uuid.uuid4())
        try:
            self._conn.execute(
                """
                INSERT INTO attachments
                    (id, report_id, tenant_id, filename, mime_type, size_bytes, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment_id,
                    report_id,
                    caller["tenant_id"],
                    filename,
                    mime_type,
                    len(data),
                    data,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.exception("upload_attachment db error")
            return _err(f"Database error: {exc}", 500)

        return _ok(
            {
                "id":         attachment_id,
                "report_id":  report_id,
                "filename":   filename,
                "size_bytes": len(data),
            },
            201,
        )
