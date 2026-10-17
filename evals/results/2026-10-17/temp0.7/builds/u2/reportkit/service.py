"""ReportService — the HTTP surface of reportkit.

Every public method accepts a *request* dict and returns a *response* dict
with at least a ``status`` (int) and ``body`` (dict) key.  No web framework
is involved; a thin WSGI/ASGI adapter (not included) would call these methods.

request dict shape
------------------
{
    "headers": {"Authorization": "Bearer <token>", ...},
    "query":   {"sort": "title", "q": "...", ...},
    "body":    {...},           # parsed JSON for JSON endpoints
    "body_bytes": b"...",       # raw bytes for attachment upload / webhooks
}
"""

import sqlite3
import uuid
from datetime import datetime, timezone

from .auth import resolve_caller, require_permission, _extract_token
from .errors import (
    NotFoundError,
    ValidationError,
    ReportkitError,
)
from .events import default_registry
from .scanner import scan


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _ok(body: dict, status: int = 200) -> dict:
    return {"status": status, "body": body}


def _err(exc: ReportkitError) -> dict:
    return {"status": exc.status, "body": {"error": exc.message}}


_ALLOWED_SORT_COLUMNS = {"created_at", "title"}


class ReportService:
    """Stateless service object; receives a db connection at construction."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _authenticate(self, request: dict) -> dict:
        token = _extract_token(request)
        return resolve_caller(self._conn, token)

    def _get_report_or_404(self, report_id: str, caller: dict) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, caller["tenant_id"]),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"Report '{report_id}' not found")
        return row

    # ------------------------------------------------------------------
    # Public HTTP surface
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """POST /reports — create a report for the authenticated caller."""
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:write")

            body: dict = request.get("body") or {}
            title = (body.get("title") or "").strip()
            if not title:
                raise ValidationError("'title' is required")
            content = body.get("body") or ""

            report_id = str(uuid.uuid4())
            now = _now()

            self._conn.execute(
                """
                INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (report_id, caller["tenant_id"], caller["user_id"], title, content, now, now),
            )
            self._conn.commit()

            default_registry.dispatch("report.created", {
                "report_id": report_id,
                "tenant_id": caller["tenant_id"],
                "owner_id":  caller["user_id"],
                "title":     title,
            })

            return _ok(
                {
                    "id":         report_id,
                    "title":      title,
                    "body":       content,
                    "owner_id":   caller["user_id"],
                    "tenant_id":  caller["tenant_id"],
                    "created_at": now,
                    "updated_at": now,
                },
                status=201,
            )
        except ReportkitError as exc:
            return _err(exc)

    def get_report(self, request: dict, report_id: str) -> dict:
        """GET /reports/<id> — return a single report."""
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:read")
            row = self._get_report_or_404(report_id, caller)
            return _ok(_row_to_dict(row))
        except ReportkitError as exc:
            return _err(exc)

    def list_reports(self, request: dict) -> dict:
        """GET /reports — the caller's own reports, newest first."""
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:read")

            rows = self._conn.execute(
                """
                SELECT * FROM reports
                WHERE  owner_id  = ?
                  AND  tenant_id = ?
                ORDER  BY created_at DESC
                """,
                (caller["user_id"], caller["tenant_id"]),
            ).fetchall()

            return _ok({"reports": [_row_to_dict(r) for r in rows]})
        except ReportkitError as exc:
            return _err(exc)

    def search_reports(self, request: dict) -> dict:
        """GET /reports/search?q=...&sort=created_at|title

        Searches the caller's own reports by title substring.
        The ``sort`` parameter is validated against an allowlist before being
        interpolated into the ORDER BY clause, preventing SQL injection from
        the user-controlled sort control.
        """
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:read")

            query_params: dict = request.get("query") or {}
            q    = (query_params.get("q") or "").strip()
            sort = (query_params.get("sort") or "created_at").strip()

            # Validate sort against explicit allowlist — never interpolate
            # user input into SQL without this check.
            if sort not in _ALLOWED_SORT_COLUMNS:
                raise ValidationError(
                    f"Invalid sort '{sort}'. Allowed: {', '.join(sorted(_ALLOWED_SORT_COLUMNS))}"
                )

            pattern = f"%{q}%"

            rows = self._conn.execute(
                f"""
                SELECT * FROM reports
                WHERE  owner_id  = ?
                  AND  tenant_id = ?
                  AND  title LIKE ?
                ORDER  BY {sort} DESC
                """,  # sort is allowlist-validated above
                (caller["user_id"], caller["tenant_id"], pattern),
            ).fetchall()

            return _ok({"reports": [_row_to_dict(r) for r in rows]})
        except ReportkitError as exc:
            return _err(exc)

    def delete_report(self, request: dict, report_id: str) -> dict:
        """DELETE /reports/<id> — delete a report."""
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:delete")

            # Verify the report exists and belongs to this tenant.
            self._get_report_or_404(report_id, caller)

            self._conn.execute(
                "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
                (report_id, caller["tenant_id"]),
            )
            self._conn.commit()

            default_registry.dispatch("report.deleted", {
                "report_id": report_id,
                "tenant_id": caller["tenant_id"],
                "actor_id":  caller["user_id"],
            })

            return _ok({"deleted": True})
        except ReportkitError as exc:
            return _err(exc)

    def upload_attachment(self, request: dict) -> dict:
        """POST /attachments — store an attachment linked to a report.

        request body keys (parsed from multipart or JSON envelope):
            report_id : str
            filename  : str
            mime_type : str  (optional)

        request["body_bytes"] : raw file bytes
        """
        try:
            caller = self._authenticate(request)
            require_permission(caller, "report:write")

            body: dict  = request.get("body") or {}
            report_id   = (body.get("report_id") or "").strip()
            filename    = (body.get("filename") or "upload").strip()
            mime_type   = (body.get("mime_type") or "application/octet-stream").strip()
            data: bytes = request.get("body_bytes") or b""

            if not report_id:
                raise ValidationError("'report_id' is required")

            # Confirm the report exists and belongs to this tenant.
            self._get_report_or_404(report_id, caller)

            # Scan before storing — raises on disallowed content or oversize.
            scan(data, filename)

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
                    caller["tenant_id"],
                    filename,
                    mime_type,
                    len(data),
                    data,
                    now,
                ),
            )
            self._conn.commit()

            return _ok(
                {
                    "id":         attachment_id,
                    "report_id":  report_id,
                    "filename":   filename,
                    "mime_type":  mime_type,
                    "size_bytes": len(data),
                    "created_at": now,
                },
                status=201,
            )
        except ReportkitError as exc:
            return _err(exc)
