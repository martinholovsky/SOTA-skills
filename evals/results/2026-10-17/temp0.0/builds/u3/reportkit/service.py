"""
ReportService — the HTTP surface.

Every public method accepts a *request* dict with the shape::

    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    {...},          # parsed JSON (dict)
        "query":   {...},          # query-string params (dict)
    }

Methods return a plain dict.  The caller (e.g. a thin WSGI/ASGI adapter)
is responsible for serialising to JSON and setting the HTTP status code.
Errors are raised as subclasses of ReportkitError; the adapter maps them
to the appropriate HTTP status via ``error.http_status``.
"""

import sqlite3
from datetime import datetime, timezone

from .auth import extract_token, require_permission, resolve_caller
from .errors import NotFoundError, ValidationError
from .events import EventRegistry, default_registry
from .ids import new_id
from .scanning import scan

# Allowed sort columns for search_reports — prevents SQL injection via
# the user-supplied sort control.
_ALLOWED_SORT_COLUMNS = {"created_at", "title"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


class ReportService:
    """
    Multi-tenant report service.

    Parameters
    ----------
    conn     : open sqlite3 connection (schema already applied)
    registry : EventRegistry to dispatch domain events through
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        registry: EventRegistry | None = None,
    ) -> None:
        self._conn = conn
        self._registry = registry or default_registry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _authenticate(self, request: dict) -> dict:
        token = extract_token(request)
        return resolve_caller(self._conn, token)

    def _get_report_or_404(self, report_id: str, tenant_id: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, tenant_id),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"Report '{report_id}' not found.")
        return row

    # ------------------------------------------------------------------
    # Public HTTP surface
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """
        Create a report for the authenticated caller.

        Body fields: ``title`` (required), ``body`` (optional).
        """
        caller = self._authenticate(request)
        require_permission(caller, "report:write")

        body = request.get("body") or {}
        title = (body.get("title") or "").strip()
        if not title:
            raise ValidationError("'title' is required.")

        content = body.get("body", "")
        report_id = new_id()
        now = _now_iso()

        self._conn.execute(
            """
            INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, caller["tenant_id"], caller["user_id"], title, content, now, now),
        )
        self._conn.commit()

        self._registry.dispatch("report.created", {
            "report_id": report_id,
            "tenant_id": caller["tenant_id"],
            "owner_id":  caller["user_id"],
        })

        return {
            "id":         report_id,
            "tenant_id":  caller["tenant_id"],
            "owner_id":   caller["user_id"],
            "title":      title,
            "body":       content,
            "created_at": now,
            "updated_at": now,
        }

    def get_report(self, request: dict, report_id: str) -> dict:
        """Return a single report belonging to the caller's tenant."""
        caller = self._authenticate(request)
        require_permission(caller, "report:read")

        row = self._get_report_or_404(report_id, caller["tenant_id"])
        return dict(row)

    def list_reports(self, request: dict) -> list[dict]:
        """
        Return the caller's own reports, newest first.

        This is the hottest query; permissions are resolved once per
        request via the session JOIN in resolve_caller().
        """
        caller = self._authenticate(request)
        require_permission(caller, "report:read")

        rows = self._conn.execute(
            """
            SELECT * FROM reports
            WHERE owner_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            """,
            (caller["user_id"], caller["tenant_id"]),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_reports(self, request: dict) -> list[dict]:
        """
        Title search across the caller's reports.

        Query params:
            ``q``    – search term (substring match)
            ``sort`` – ``created_at`` (default) or ``title``
        """
        caller = self._authenticate(request)
        require_permission(caller, "report:read")

        query_params = request.get("query") or {}
        search_term  = query_params.get("q", "")
        sort_col     = query_params.get("sort", "created_at")

        # Validate sort column against allowlist — the value comes from
        # the UI and must not be interpolated directly into SQL.
        if sort_col not in _ALLOWED_SORT_COLUMNS:
            raise ValidationError(
                f"Invalid sort column '{sort_col}'. "
                f"Allowed: {sorted(_ALLOWED_SORT_COLUMNS)}."
            )

        rows = self._conn.execute(
            f"""
            SELECT * FROM reports
            WHERE owner_id = ?
              AND tenant_id = ?
              AND title LIKE ?
            ORDER BY {sort_col} DESC
            """,
            (caller["user_id"], caller["tenant_id"], f"%{search_term}%"),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_report(self, request: dict, report_id: str) -> dict:
        """
        Delete a report.

        Admins may delete any report in their tenant.
        Editors/viewers may only delete their own reports (editors have
        report:write but not report:delete; only admins carry
        report:delete).
        """
        caller = self._authenticate(request)
        require_permission(caller, "report:delete")

        # Confirm the report exists within the tenant before deleting.
        self._get_report_or_404(report_id, caller["tenant_id"])

        self._conn.execute(
            "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, caller["tenant_id"]),
        )
        self._conn.commit()

        self._registry.dispatch("report.deleted", {
            "report_id": report_id,
            "tenant_id": caller["tenant_id"],
            "actor_id":  caller["user_id"],
        })

        return {"deleted": True, "report_id": report_id}

    def upload_attachment(self, request: dict) -> dict:
        """
        Store an attachment after content scanning.

        Body fields:
            ``report_id`` – target report (required)
            ``filename``  – original filename (required)
            ``mime_type`` – MIME type (optional)
            ``data``      – raw bytes or base64-encoded string (required)
        """
        caller = self._authenticate(request)
        require_permission(caller, "report:write")

        body = request.get("body") or {}
        report_id = body.get("report_id", "")
        filename  = (body.get("filename") or "").strip()
        mime_type = body.get("mime_type", "application/octet-stream")
        raw_data  = body.get("data", b"")

        if not report_id:
            raise ValidationError("'report_id' is required.")
        if not filename:
            raise ValidationError("'filename' is required.")

        # Accept bytes or a UTF-8 string (e.g. base64 decoded by adapter).
        if isinstance(raw_data, str):
            raw_data = raw_data.encode("latin-1")

        # Content scan — raises ContentPolicyError on violation.
        scan(raw_data, filename)

        # Confirm the report exists and belongs to this tenant.
        self._get_report_or_404(report_id, caller["tenant_id"])

        attachment_id = new_id()
        now = _now_iso()

        self._conn.execute(
            """
            INSERT INTO attachments
                (id, report_id, tenant_id, filename, mime_type, size_bytes, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment_id,
                report_id,
                caller["tenant_id"],
                filename,
                mime_type,
                len(raw_data),
                raw_data,
                now,
            ),
        )
        self._conn.commit()

        return {
            "id":         attachment_id,
            "report_id":  report_id,
            "filename":   filename,
            "mime_type":  mime_type,
            "size_bytes": len(raw_data),
            "created_at": now,
        }
