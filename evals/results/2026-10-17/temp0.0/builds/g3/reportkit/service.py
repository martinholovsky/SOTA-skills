"""
ReportService — the HTTP surface.

Each public method takes a `request` dict and returns a response dict.
Authentication, authorization, rate-limiting, and input validation are
applied at the top of every handler before any business logic.

Request dict shape (callers supply what they need):
    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    {...},          # parsed JSON
        "query":   {...},          # query-string parameters
        "files":   {               # for upload_attachment
            "file": {"filename": str, "content_type": str, "data": bytes}
        },
    }

Response dict shape:
    {"status": int, "body": {...}}
"""

import datetime
import sqlite3
import uuid
from typing import Any

from .audit import record as audit_record
from .auth import resolve_principal, Principal
from .config import Config
from .db import REPORT_SORT_COLUMNS, DEFAULT_SORT_COLUMN
from .errors import (
    BadRequest, Forbidden, NotFound, ReportkitError,
    PayloadTooLarge, UnsupportedMediaType,
)
from .events import dispatch
from .logging import get_logger
from .rate_limit import RateLimiter
from .scanner import scan
from .validation import (
    extract_bearer_token,
    require_title,
    require_body,
    require_uuid,
    require_sort_key,
    require_filename,
    require_mime_type,
    require_bytes,
)

logger = get_logger(__name__)


class ReportService:
    """
    Multi-tenant report service.

    Parameters
    ----------
    db:
        An open sqlite3 connection (WAL mode, foreign keys on).
    rate_limiter:
        Optional RateLimiter instance; a default one is created if omitted.
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._db = db
        self._rl = rate_limiter or RateLimiter(
            window_seconds=Config.RATE_LIMIT_WINDOW_SECONDS,
            max_requests=Config.RATE_LIMIT_MAX_REQUESTS,
        )

    # ------------------------------------------------------------------
    # Public HTTP surface
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """Create a report for the authenticated caller."""
        principal = self._authenticate(request)
        self._rate_limit(principal, "create_report")
        principal.require("report:write")

        body = request.get("body") or {}
        title = require_title(body.get("title"))
        content = require_body(body.get("body", ""))

        report_id = _new_uuid()
        now = _utcnow()

        self._db.execute(
            """
            INSERT INTO reports (id, tenant_id, owner_id, title, body,
                                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, principal.tenant_id, principal.user_id,
             title, content, now, now),
        )
        audit_record(
            self._db,
            action="report.create",
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
            target_type="report",
            target_id=report_id,
        )
        self._db.commit()

        dispatch("report.created", {
            "report_id": report_id,
            "tenant_id": principal.tenant_id,
            "owner_id": principal.user_id,
        })

        logger.info(
            "report_created",
            extra={
                "report_id": report_id,
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
            },
        )
        return _ok(201, {"id": report_id, "title": title, "created_at": now})

    def get_report(self, request: dict, report_id: str) -> dict:
        """Return a single report owned by the caller's tenant."""
        principal = self._authenticate(request)
        self._rate_limit(principal, "get_report")
        principal.require("report:read")

        report_id = require_uuid(report_id, "report_id")

        # Ownership check is part of the query (rules/03 §2).
        row = self._db.execute(
            """
            SELECT id, title, body, owner_id, created_at, updated_at
            FROM   reports
            WHERE  id = ? AND tenant_id = ?
            """,
            (report_id, principal.tenant_id),
        ).fetchone()

        if row is None:
            # 404 regardless of whether the report exists in another tenant
            # (rules/03 §2 — don't leak existence via 403 vs 404).
            raise NotFound("Report not found")

        return _ok(200, _report_row_to_dict(row))

    def list_reports(self, request: dict) -> dict:
        """Return the caller's own reports, newest first."""
        principal = self._authenticate(request)
        self._rate_limit(principal, "list_reports")
        principal.require("report:read")

        rows = self._db.execute(
            """
            SELECT id, title, body, owner_id, created_at, updated_at
            FROM   reports
            WHERE  tenant_id = ? AND owner_id = ?
            ORDER  BY created_at DESC
            """,
            (principal.tenant_id, principal.user_id),
        ).fetchall()

        return _ok(200, {"reports": [_report_row_to_dict(r) for r in rows]})

    def search_reports(self, request: dict) -> dict:
        """
        Title search across the caller's reports.

        Accepts an optional `sort` query parameter (`created_at` or `title`).
        The sort key is validated against a hard-coded allowlist before being
        interpolated into the ORDER BY clause (rules/01 §2 — identifiers cannot
        be parameterised; use an allowlist dict).
        """
        principal = self._authenticate(request)
        self._rate_limit(principal, "search_reports")
        principal.require("report:read")

        query_params = request.get("query") or {}

        # Validate sort key against allowlist.
        raw_sort = query_params.get("sort", DEFAULT_SORT_COLUMN)
        sort_key = require_sort_key(raw_sort)
        # Map through the DB allowlist dict — KeyError is impossible here
        # because require_sort_key already validated against the same set,
        # but the double-check makes the injection prevention explicit.
        sort_col = REPORT_SORT_COLUMNS[sort_key]

        q = query_params.get("q", "")
        if not isinstance(q, str):
            raise BadRequest("'q' must be a string")
        q = q.strip()
        if len(q) > 500:
            raise BadRequest("'q' must be 500 characters or fewer")

        # LIKE wildcard characters in the search term are escaped so the user
        # cannot control match breadth (rules/01 §2 — LIKE clause escaping).
        escaped_q = _escape_like(q)
        pattern = f"%{escaped_q}%"

        # ORDER BY uses the validated column name, not user input directly.
        sql = f"""
            SELECT id, title, body, owner_id, created_at, updated_at
            FROM   reports
            WHERE  tenant_id = ? AND owner_id = ?
              AND  title LIKE ? ESCAPE '\\'
            ORDER  BY {sort_col}
        """
        rows = self._db.execute(
            sql,
            (principal.tenant_id, principal.user_id, pattern),
        ).fetchall()

        return _ok(200, {"reports": [_report_row_to_dict(r) for r in rows]})

    def delete_report(self, request: dict, report_id: str) -> dict:
        """Delete a report.  Requires report:delete (admin only)."""
        principal = self._authenticate(request)
        self._rate_limit(principal, "delete_report")
        principal.require("report:delete")

        report_id = require_uuid(report_id, "report_id")

        # Ownership check is part of the query (rules/03 §2).
        row = self._db.execute(
            "SELECT id FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, principal.tenant_id),
        ).fetchone()

        if row is None:
            raise NotFound("Report not found")

        self._db.execute(
            "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
            (report_id, principal.tenant_id),
        )
        audit_record(
            self._db,
            action="report.delete",
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
            target_type="report",
            target_id=report_id,
        )
        self._db.commit()

        dispatch("report.deleted", {
            "report_id": report_id,
            "tenant_id": principal.tenant_id,
            "deleted_by": principal.user_id,
        })

        logger.info(
            "report_deleted",
            extra={
                "report_id": report_id,
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
            },
        )
        return _ok(204, {})

    def upload_attachment(self, request: dict) -> dict:
        """
        Store an attachment after content scanning.

        The file is passed in request["files"]["file"] as a dict with keys:
            filename     : str
            content_type : str
            data         : bytes
        """
        principal = self._authenticate(request)
        self._rate_limit(principal, "upload_attachment")
        principal.require("report:write")

        files = request.get("files") or {}
        file_info = files.get("file")
        if not file_info or not isinstance(file_info, dict):
            raise BadRequest("'file' upload is required")

        filename = require_filename(file_info.get("filename", ""))
        content_type = require_mime_type(file_info.get("content_type", ""))

        # Validate MIME type against allowlist (rules/01 §1 — allowlist).
        if content_type not in Config.ALLOWED_ATTACHMENT_MIME_TYPES:
            raise UnsupportedMediaType(
                f"Content type '{content_type}' is not permitted"
            )

        data = require_bytes(
            file_info.get("data", b""),
            "file.data",
            Config.MAX_ATTACHMENT_BYTES,
        )

        # Scan before storing (spec requirement).
        is_clean, reason = scan(data, filename)
        if not is_clean:
            logger.warning(
                "attachment_rejected",
                extra={
                    "tenant_id": principal.tenant_id,
                    "user_id": principal.user_id,
                    "filename": filename,
                    "reason": reason,
                },
            )
            raise BadRequest(f"Attachment rejected: {reason}")

        # Server-generated storage key — user filename is metadata only
        # (rules/01 §4 — best practice: don't use user input as a path).
        storage_key = _new_uuid()
        attachment_id = _new_uuid()
        now = _utcnow()

        self._db.execute(
            """
            INSERT INTO attachments
                (id, tenant_id, owner_id, filename, size_bytes,
                 scan_status, storage_key, created_at)
            VALUES (?, ?, ?, ?, ?, 'clean', ?, ?)
            """,
            (
                attachment_id,
                principal.tenant_id,
                principal.user_id,
                filename,
                len(data),
                storage_key,
                now,
            ),
        )
        audit_record(
            self._db,
            action="attachment.upload",
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
            target_type="attachment",
            target_id=attachment_id,
            detail={"filename": filename, "size_bytes": len(data)},
        )
        self._db.commit()

        logger.info(
            "attachment_uploaded",
            extra={
                "attachment_id": attachment_id,
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
                "size_bytes": len(data),
            },
        )
        return _ok(201, {
            "id": attachment_id,
            "storage_key": storage_key,
            "filename": filename,
            "size_bytes": len(data),
            "created_at": now,
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _authenticate(self, request: dict) -> Principal:
        token = extract_bearer_token(request)
        return resolve_principal(self._db, token)

    def _rate_limit(self, principal: Principal, endpoint: str) -> None:
        self._rl.check(principal.tenant_id, endpoint)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _ok(status: int, body: dict) -> dict:
    return {"status": status, "body": body}


def _report_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "owner_id": row["owner_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters % and _ in a search value (rules/01 §2)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
