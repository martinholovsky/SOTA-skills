"""
ReportService — the HTTP surface.

Each public method accepts a *request* dict and returns a response dict of the
form::

    {"status": <int>, "body": <json-serialisable dict>}

Authentication is via a bearer token resolved through the sessions table.

The class is intentionally framework-agnostic: a thin WSGI/ASGI adapter (not
part of this package) would translate real HTTP objects into the expected dict
shape.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from reportkit.auth import AuthError, require_permission, resolve_caller
from reportkit.content_scan import ContentViolation, scan
from reportkit.events import EventRegistry, default_registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed sort columns for search_reports — validated against a whitelist to
# prevent SQL injection via user-supplied sort values.
# ---------------------------------------------------------------------------
_ALLOWED_SORT_COLUMNS = {"created_at", "title"}
_DEFAULT_SORT = "created_at"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ok(body: Any, status: int = 200) -> dict:
    return {"status": status, "body": body}


def _err(message: str, status: int) -> dict:
    return {"status": status, "body": {"error": message}}


class ReportService:
    """
    Multi-tenant report service.

    Parameters
    ----------
    conn:
        An open :class:`sqlite3.Connection` with the reportkit schema applied.
    registry:
        An :class:`~reportkit.events.EventRegistry` for domain events.
        Defaults to the module-level ``default_registry``.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        registry: EventRegistry | None = None,
    ) -> None:
        self._conn = conn
        self._registry = registry or default_registry

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """Create a report owned by the authenticated caller."""
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:write")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        data = request.get("body") or {}
        title = (data.get("title") or "").strip()
        body  = (data.get("body")  or "").strip()

        if not title:
            return _err("'title' is required.", 400)

        report_id = str(uuid.uuid4())
        now = _now_iso()

        self._conn.execute(
            """
            INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, caller["tenant_id"], caller["user_id"], title, body, now, now),
        )
        self._conn.commit()

        report = self._fetch_report(report_id)
        self._registry.dispatch("report.created", {"report_id": report_id, "caller": caller})
        logger.info("Report %s created by user %s.", report_id, caller["user_id"])
        return _ok(dict(report), status=201)

    def get_report(self, request: dict, report_id: str) -> dict:
        """Return a single report by *report_id*."""
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:read")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        report = self._fetch_report(report_id)
        if report is None:
            return _err("Report not found.", 404)

        # Tenant isolation: callers may only read reports in their own tenant.
        if report["tenant_id"] != caller["tenant_id"]:
            return _err("Report not found.", 404)

        return _ok(dict(report))

    def list_reports(self, request: dict) -> dict:
        """Return the caller's own reports, newest first."""
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:read")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        rows = self._conn.execute(
            """
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports
            WHERE owner_id = ?
            ORDER BY created_at DESC
            """,
            (caller["user_id"],),
        ).fetchall()

        return _ok({"reports": [dict(r) for r in rows]})

    def search_reports(self, request: dict) -> dict:
        """
        Full-text title search across the caller's own reports.

        Query parameters (from ``request["query"]``):
        - ``q``    – search term (required)
        - ``sort`` – ``created_at`` (default) or ``title``
        """
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:read")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        query_params = request.get("query") or {}
        term = (query_params.get("q") or "").strip()
        if not term:
            return _err("Query parameter 'q' is required.", 400)

        # Validate sort column against whitelist — never interpolate raw user
        # input into SQL.
        sort_raw = (query_params.get("sort") or _DEFAULT_SORT).strip()
        sort_col = sort_raw if sort_raw in _ALLOWED_SORT_COLUMNS else _DEFAULT_SORT

        # SQLite LIKE search; we escape '%' and '_' so they are treated as
        # literals, then wrap with '%' wildcards ourselves.
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"

        sql = f"""
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports
            WHERE owner_id = ?
              AND title LIKE ? ESCAPE '\\'
            ORDER BY {sort_col} ASC
        """
        rows = self._conn.execute(sql, (caller["user_id"], pattern)).fetchall()
        return _ok({"reports": [dict(r) for r in rows]})

    def delete_report(self, request: dict, report_id: str) -> dict:
        """Delete a report.  Requires ``report:delete`` permission."""
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:delete")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        report = self._fetch_report(report_id)
        if report is None:
            return _err("Report not found.", 404)

        if report["tenant_id"] != caller["tenant_id"]:
            return _err("Report not found.", 404)

        self._conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self._conn.commit()

        self._registry.dispatch(
            "report.deleted",
            {"report_id": report_id, "caller": caller},
        )
        logger.info("Report %s deleted by user %s.", report_id, caller["user_id"])
        return _ok({"deleted": True})

    def upload_attachment(self, request: dict) -> dict:
        """
        Store an attachment after scanning for disallowed content.

        Expected ``request`` keys:
        - ``body["report_id"]`` – the report this attachment belongs to
        - ``body["filename"]``  – original filename
        - ``body["mime_type"]`` – MIME type string
        - ``body["data"]``      – raw ``bytes`` of the file
        """
        try:
            caller = resolve_caller(self._conn, request)
            require_permission(caller, "report:write")
        except AuthError as exc:
            return _err(str(exc), exc.status)

        data    = request.get("body") or {}
        report_id = (data.get("report_id") or "").strip()
        filename  = (data.get("filename")  or "").strip()
        mime_type = (data.get("mime_type") or "application/octet-stream").strip()
        file_data: bytes = data.get("data", b"")

        if not report_id:
            return _err("'report_id' is required.", 400)
        if not filename:
            return _err("'filename' is required.", 400)
        if not isinstance(file_data, (bytes, bytearray)):
            return _err("'data' must be bytes.", 400)

        # Verify the report exists and belongs to the caller's tenant.
        report = self._fetch_report(report_id)
        if report is None or report["tenant_id"] != caller["tenant_id"]:
            return _err("Report not found.", 404)

        # Content scan — raises ContentViolation or ValueError on failure.
        try:
            scan(bytes(file_data), filename=filename)
        except ContentViolation as exc:
            return _err(f"Attachment rejected: {exc}", 422)
        except ValueError as exc:
            return _err(str(exc), 413)

        attachment_id = str(uuid.uuid4())
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
                len(file_data),
                file_data,
            ),
        )
        self._conn.commit()
        logger.info(
            "Attachment %s (%s, %d bytes) stored for report %s.",
            attachment_id,
            filename,
            len(file_data),
            report_id,
        )
        return _ok(
            {
                "id":         attachment_id,
                "report_id":  report_id,
                "filename":   filename,
                "mime_type":  mime_type,
                "size_bytes": len(file_data),
            },
            status=201,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_report(self, report_id: str):
        return self._conn.execute(
            """
            SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
            FROM reports WHERE id = ?
            """,
            (report_id,),
        ).fetchone()
