"""
ReportKit HTTP surface.

Each public method takes a `request` dict and returns a `response` dict:
    {"status": int, "body": dict}

Request shape:
    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    {...},            # parsed JSON, for POST/PUT
        "query":   {...},            # URL query parameters
        "remote_addr": "1.2.3.4",   # caller IP (set by the transport layer)
    }

Security controls applied unconditionally on every request:
  (a) Rate limiting — per authenticated user (api scope).
  (b) Transport: TLS is enforced at the transport/gateway layer (see NOTES.md).
  (c) Tests: see tests/.
  (d) Structured logging without secrets/PII.

BILLING WEBHOOK notes:
  Rate limiting is keyed on remote_addr (webhook scope).
  HMAC verification runs before any body parsing.
  Idempotency is enforced via billing_events primary key.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from . import audit, events
from .auth import (
    AuthError,
    Principal,
    require_permission,
    require_tenant_owner,
    resolve_session,
)
from .crypto import generate_id, generate_storage_key, verify_hmac_sha256
from .rate_limit import RateLimitExceeded, check_and_increment
from .scanner import is_clean
from .validation import (
    ValidationError,
    extract_bearer_token,
    validate_amount_cents,
    validate_body,
    validate_content_type,
    validate_event_id,
    validate_filename,
    validate_search_query,
    validate_sort_col,
    validate_title,
    validate_uuid,
)

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MiB


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ok(body: dict) -> dict:
    return {"status": 200, "body": body}


def _created(body: dict) -> dict:
    return {"status": 201, "body": body}


def _err(status: int, message: str) -> dict:
    # message is safe to return: it never contains PII or internal detail.
    return {"status": status, "body": {"error": message}}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authenticate(conn: sqlite3.Connection, request: dict) -> Principal:
    """Extract bearer token and resolve to a Principal. Raises AuthError."""
    token = extract_bearer_token(request)
    return resolve_session(conn, token)


def _rate_limit_api(conn: sqlite3.Connection, user_id: str) -> None:
    check_and_increment(conn, "api", user_id)


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class ReportService:
    """
    Multi-tenant report service.

    All methods return {"status": int, "body": dict}.
    They never raise; exceptions are caught and mapped to error responses.
    """

    def __init__(self, conn: sqlite3.Connection, webhook_secret: bytes | None = None):
        """
        conn            — SQLite connection (caller manages lifecycle).
        webhook_secret  — raw bytes of the HMAC secret for billing webhooks.
                          If None, webhook verification is disabled (test mode only).
        """
        self._conn = conn
        self._webhook_secret = webhook_secret

    # ------------------------------------------------------------------
    # CREATE REPORT
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """
        POST /reports
        Requires: report:write
        Body: {"title": str, "body": str}
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:write")

            body = request.get("body") or {}
            title = validate_title(body.get("title"))
            content = validate_body(body.get("body", ""))

            report_id = generate_id()
            now = _now_iso()

            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (report_id, principal.tenant_id, principal.user_id, title, content, now, now),
            )
            audit.log(
                conn,
                action="report.created",
                actor_id=principal.user_id,
                tenant_id=principal.tenant_id,
                target_type="report",
                target_id=report_id,
                detail={"title_len": len(title)},
            )
            conn.execute("COMMIT")

            events.dispatch(events.EVENT_REPORT_CREATED, {
                "report_id": report_id,
                "tenant_id": principal.tenant_id,
                "owner_id":  principal.user_id,
            })

            logger.info(
                "report_created",
                extra={
                    "rk_action":    "report.created",
                    "rk_report_id": report_id,
                    "rk_tenant_id": principal.tenant_id,
                },
            )
            return _created({"id": report_id, "title": title, "created_at": now})

        except ValidationError as exc:
            conn.execute("ROLLBACK")
            return _err(400, str(exc))
        except AuthError as exc:
            conn.execute("ROLLBACK")
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            conn.execute("ROLLBACK")
            return _err(429, "rate limit exceeded")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("create_report_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # GET REPORT
    # ------------------------------------------------------------------

    def get_report(self, request: dict, report_id: str) -> dict:
        """
        GET /reports/{report_id}
        Requires: report:read, same tenant
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:read")

            rid = validate_uuid(report_id, "report_id")

            # Ownership is part of the query — not a fetch-then-check.
            # We filter on tenant_id so cross-tenant IDs return 404, not 403,
            # avoiding existence leakage.
            row = conn.execute(
                """
                SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
                FROM   reports
                WHERE  id = ?
                  AND  tenant_id = ?
                """,
                (rid, principal.tenant_id),
            ).fetchone()

            if row is None:
                return _err(404, "report not found")

            return _ok({
                "id":         row["id"],
                "title":      row["title"],
                "body":       row["body"],
                "owner_id":   row["owner_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })

        except ValidationError as exc:
            return _err(400, str(exc))
        except AuthError as exc:
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            return _err(429, "rate limit exceeded")
        except Exception:
            logger.exception("get_report_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # LIST REPORTS
    # ------------------------------------------------------------------

    def list_reports(self, request: dict) -> dict:
        """
        GET /reports
        Requires: report:read
        Returns: caller's own reports, newest first.
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:read")

            rows = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM   reports r
                WHERE  r.tenant_id = ?
                  AND  r.owner_id  = ?
                ORDER BY r.created_at DESC
                """,
                (principal.tenant_id, principal.user_id),
            ).fetchall()

            return _ok({"reports": [dict(r) for r in rows]})

        except AuthError as exc:
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            return _err(429, "rate limit exceeded")
        except Exception:
            logger.exception("list_reports_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # SEARCH REPORTS
    # ------------------------------------------------------------------

    def search_reports(self, request: dict) -> dict:
        """
        GET /reports/search?q=<term>&sort=<created_at|title>
        Requires: report:read
        Searches titles across the caller's own reports.

        Sort column is validated against an allowlist (SQL identifiers cannot
        be parameterized).  The search term is passed as a SQL parameter with
        LIKE wildcards; % and _ in the term are escaped so the caller controls
        match breadth.
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:read")

            query_params = request.get("query") or {}
            raw_q    = query_params.get("q", "")
            raw_sort = query_params.get("sort")

            q        = validate_search_query(raw_q)
            sort_col = validate_sort_col(raw_sort)  # returns safe SQL column expression

            # Escape LIKE metacharacters in the search term so the caller
            # controls match breadth (parameterization doesn't escape % and _).
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like_pattern = f"%{escaped}%"

            # sort_col is a value from SORT_COL_ALLOWLIST (e.g. "r.created_at"),
            # not user input — safe to interpolate.
            sql = f"""
                SELECT id, title, created_at, updated_at
                FROM   reports r
                WHERE  r.tenant_id = ?
                  AND  r.owner_id  = ?
                  AND  r.title LIKE ? ESCAPE '\\'
                ORDER BY {sort_col} DESC
            """

            rows = conn.execute(
                sql,
                (principal.tenant_id, principal.user_id, like_pattern),
            ).fetchall()

            return _ok({"reports": [dict(r) for r in rows]})

        except ValidationError as exc:
            return _err(400, str(exc))
        except AuthError as exc:
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            return _err(429, "rate limit exceeded")
        except Exception:
            logger.exception("search_reports_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # DELETE REPORT
    # ------------------------------------------------------------------

    def delete_report(self, request: dict, report_id: str) -> dict:
        """
        DELETE /reports/{report_id}
        Requires: report:delete (admin only)
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:delete")

            rid = validate_uuid(report_id, "report_id")

            conn.execute("BEGIN")

            # Ownership check is part of the query.
            row = conn.execute(
                "SELECT id, tenant_id FROM reports WHERE id = ? AND tenant_id = ?",
                (rid, principal.tenant_id),
            ).fetchone()

            if row is None:
                conn.execute("ROLLBACK")
                return _err(404, "report not found")

            conn.execute("DELETE FROM reports WHERE id = ? AND tenant_id = ?",
                         (rid, principal.tenant_id))

            audit.log(
                conn,
                action="report.deleted",
                actor_id=principal.user_id,
                tenant_id=principal.tenant_id,
                target_type="report",
                target_id=rid,
            )
            conn.execute("COMMIT")

            events.dispatch(events.EVENT_REPORT_DELETED, {
                "report_id": rid,
                "tenant_id": principal.tenant_id,
                "actor_id":  principal.user_id,
            })

            logger.info(
                "report_deleted",
                extra={
                    "rk_action":    "report.deleted",
                    "rk_report_id": rid,
                    "rk_tenant_id": principal.tenant_id,
                },
            )
            return _ok({"deleted": rid})

        except ValidationError as exc:
            conn.execute("ROLLBACK")
            return _err(400, str(exc))
        except AuthError as exc:
            conn.execute("ROLLBACK")
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            conn.execute("ROLLBACK")
            return _err(429, "rate limit exceeded")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("delete_report_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # UPLOAD ATTACHMENT
    # ------------------------------------------------------------------

    def upload_attachment(self, request: dict) -> dict:
        """
        POST /attachments
        Requires: report:write (caller must own the target report)
        Body keys: report_id, filename, content_type, data (bytes)

        The attachment data arrives as raw bytes in request["body"]["data"].
        The storage key is server-generated (UUID); the original filename is
        stored for display only and never used as a filesystem path.
        """
        conn = self._conn
        try:
            principal = _authenticate(conn, request)
            _rate_limit_api(conn, principal.user_id)
            require_permission(principal, "report:write")

            body = request.get("body") or {}

            report_id    = validate_uuid(body.get("report_id", ""), "report_id")
            filename     = validate_filename(body.get("filename"))
            content_type = validate_content_type(body.get("content_type"))
            data         = body.get("data")

            if not isinstance(data, (bytes, bytearray)):
                return _err(400, "data: must be bytes")
            if len(data) == 0:
                return _err(400, "data: must not be empty")
            if len(data) > MAX_ATTACHMENT_BYTES:
                return _err(413, f"attachment exceeds {MAX_ATTACHMENT_BYTES} bytes")

            # Verify the target report exists and belongs to this tenant+user.
            report_row = conn.execute(
                "SELECT id, tenant_id, owner_id FROM reports WHERE id = ? AND tenant_id = ?",
                (report_id, principal.tenant_id),
            ).fetchone()

            if report_row is None:
                return _err(404, "report not found")

            # Scan before storing.
            if not is_clean(bytes(data)):
                logger.warning(
                    "attachment_rejected_by_scanner",
                    extra={
                        "rk_tenant_id": principal.tenant_id,
                        "rk_report_id": report_id,
                        "rk_size":      len(data),
                    },
                )
                return _err(422, "attachment rejected by content scanner")

            attachment_id  = generate_id()
            storage_key    = generate_storage_key()
            now            = _now_iso()

            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO attachments
                    (id, report_id, tenant_id, original_name, storage_key,
                     size_bytes, content_type, scan_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'clean', ?)
                """,
                (
                    attachment_id, report_id, principal.tenant_id,
                    filename, storage_key, len(data), content_type, now,
                ),
            )
            audit.log(
                conn,
                action="attachment.uploaded",
                actor_id=principal.user_id,
                tenant_id=principal.tenant_id,
                target_type="attachment",
                target_id=attachment_id,
                detail={"size_bytes": len(data), "content_type": content_type},
            )
            conn.execute("COMMIT")

            logger.info(
                "attachment_uploaded",
                extra={
                    "rk_action":        "attachment.uploaded",
                    "rk_attachment_id": attachment_id,
                    "rk_tenant_id":     principal.tenant_id,
                    "rk_size":          len(data),
                },
            )
            return _created({
                "id":           attachment_id,
                "storage_key":  storage_key,
                "size_bytes":   len(data),
                "created_at":   now,
            })

        except ValidationError as exc:
            conn.execute("ROLLBACK")
            return _err(400, str(exc))
        except AuthError as exc:
            conn.execute("ROLLBACK")
            return _err(exc.status, str(exc))
        except RateLimitExceeded:
            conn.execute("ROLLBACK")
            return _err(429, "rate limit exceeded")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("upload_attachment_error")
            return _err(500, "internal error")

    # ------------------------------------------------------------------
    # BILLING WEBHOOK
    # ------------------------------------------------------------------

    def billing_webhook(self, request: dict) -> dict:
        """
        POST /webhooks/billing
        Verifies HMAC-SHA256 signature before any body parsing.
        Idempotent: duplicate event IDs are silently accepted (200).
        Rate-limited per remote_addr (webhook scope).

        Request shape:
            {
                "headers": {"X-Signature": "sha256=<hex>", ...},
                "raw_body": bytes,          # unparsed body
                "body":     {...},          # pre-parsed JSON (same content)
                "remote_addr": "1.2.3.4",
            }
        """
        conn = self._conn
        remote_addr = request.get("remote_addr", "unknown")

        try:
            # Rate limit before any processing (keyed on remote IP).
            check_and_increment(conn, "webhook", remote_addr)

            # --- HMAC verification BEFORE body parsing ---
            raw_body = request.get("raw_body")
            if not isinstance(raw_body, (bytes, bytearray)):
                return _err(400, "missing raw body")

            if self._webhook_secret is None:
                # Only acceptable in tests; enforced at startup in production.
                logger.warning("webhook_secret_not_configured")
            else:
                sig_header = request.get("headers", {}).get("X-Signature", "")
                if not isinstance(sig_header, str) or not sig_header.startswith("sha256="):
                    return _err(401, "missing or malformed X-Signature")
                provided_hex = sig_header[len("sha256="):]
                if not verify_hmac_sha256(self._webhook_secret, bytes(raw_body), provided_hex):
                    logger.warning(
                        "webhook_signature_invalid remote=%s",
                        remote_addr[:45],  # cap log length
                    )
                    return _err(401, "invalid signature")

            # --- Parse and validate body ---
            body = request.get("body") or {}

            event_id   = validate_event_id(body.get("id", ""))
            event_type = body.get("type", "")
            if not isinstance(event_type, str) or not event_type:
                return _err(400, "type: required")
            tenant_id_raw = body.get("tenant_id", "")
            tenant_id  = validate_uuid(tenant_id_raw, "tenant_id")

            # Only process invoice.paid; acknowledge others without action.
            if event_type != "invoice.paid":
                return _ok({"received": True})

            amount_cents = validate_amount_cents(body.get("amount_cents", 0))

            # --- Idempotency: ignore duplicate deliveries ---
            existing = conn.execute(
                "SELECT id FROM billing_events WHERE id = ?",
                (event_id,),
            ).fetchone()
            if existing:
                logger.info(
                    "billing_webhook_duplicate event_id_prefix=%s",
                    event_id[:8],
                )
                return _ok({"received": True})

            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO billing_events (id, tenant_id, event_type, amount_cents)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, tenant_id, event_type, amount_cents),
            )
            audit.log(
                conn,
                action="billing.invoice_paid",
                tenant_id=tenant_id,
                target_type="billing_event",
                target_id=event_id,
                detail={"amount_cents": amount_cents},
            )
            conn.execute("COMMIT")

            logger.info(
                "billing_webhook_processed",
                extra={
                    "rk_action":      "billing.invoice_paid",
                    "rk_tenant_id":   tenant_id,
                    "rk_event_id_px": event_id[:8],
                },
            )
            return _ok({"received": True})

        except ValidationError as exc:
            conn.execute("ROLLBACK")
            return _err(400, str(exc))
        except RateLimitExceeded:
            conn.execute("ROLLBACK")
            return _err(429, "rate limit exceeded")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("billing_webhook_error")
            return _err(500, "internal error")
