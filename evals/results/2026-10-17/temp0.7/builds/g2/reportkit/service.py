"""
Core service layer — all business logic lives here.

Rules applied (cross-reference)
--------------------------------
- rules/01 §2 : parameterised queries throughout; identifiers via allowlist.
- rules/01 §4 : attachments stored under a server-generated UUID key; user
                filename is display metadata only.
- rules/01 §1 : all input validated at the trust boundary (validate_* calls
                at the top of each method).
- rules/03 §1 : deny by default; require_permission called before any data
                access.
- rules/03 §2 : ownership predicate in every query (tenant_id + owner_id).
- rules/03 §5 : tenant_id always from the authenticated session, never from
                the request body.
- rules/02 §8 : webhook HMAC verified over raw body before any parsing.
- Non-negotiable §a: rate limiter checked first on every public method.
- Non-negotiable §d: structured logging via logger; no secrets/PII in logs.
"""

import json
import logging
import time
import uuid

from .auth import authenticate, require_permission, AuthError
from .audit import log as audit_log
from .crypto import verify_webhook_hmac
from .events import dispatch
from .models import MAX_ATTACHMENT_BYTES
from .rate_limit import default_limiter
from .scanner import scan
from .validation import (
    validate_uuid,
    validate_title,
    validate_body,
    validate_sort,
    validate_search_query,
    validate_role,
    validate_mime_type,
    validate_filename,
    ValidationError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> int:
    return int(time.time())


def _new_id() -> str:
    return str(uuid.uuid4())


def _rate_check(principal: dict) -> None:
    if not default_limiter.check(principal["tenant_id"], principal["user_id"]):
        raise _TooManyRequests()


class _TooManyRequests(Exception):
    status = 429


def _ok(data=None) -> dict:
    return {"status": 200, "body": data or {}}


def _err(status: int, message: str) -> dict:
    return {"status": status, "body": {"error": message}}


def _handle_errors(fn):
    """Decorator: translate domain exceptions to response dicts."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValidationError as exc:
            return _err(400, str(exc))
        except AuthError as exc:
            return _err(exc.status, str(exc))
        except _TooManyRequests:
            return _err(429, "Rate limit exceeded")
        except Exception:
            logger.exception("unhandled_error")
            return _err(500, "Internal server error")

    return wrapper


# ---------------------------------------------------------------------------
# ReportService
# ---------------------------------------------------------------------------

class ReportService:
    """
    HTTP surface for the report domain.

    Each method takes a ``request`` dict:
        {
            "headers": {"Authorization": "Bearer <token>", ...},
            "body":    {...},          # parsed JSON
            "query":   {...},          # query-string params
        }

    Transport (TLS) and HSTS are enforced at the reverse-proxy layer
    (non-negotiable §b).  This class assumes it receives only HTTPS
    traffic; a deployment note in NOTES.md records that assumption.
    """

    def __init__(self, db):
        self._db = db

    # ------------------------------------------------------------------
    # create_report
    # ------------------------------------------------------------------

    @_handle_errors
    def create_report(self, request: dict) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:write")

        body = request.get("body") or {}
        title = validate_title(body.get("title", ""), "title")
        content = validate_body(body.get("body", ""), "body")

        report_id = _new_id()
        now = _now()

        db.execute(
            """
            INSERT INTO reports(id, tenant_id, owner_id, title, body,
                                created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                principal["tenant_id"],   # from session — never from body
                principal["user_id"],
                title,
                content,
                now,
                now,
            ),
        )
        audit_log(
            db,
            "report.created",
            actor_id=principal["user_id"],
            tenant_id=principal["tenant_id"],
            target_id=report_id,
        )
        db.commit()

        dispatch("report.created", {
            "report_id": report_id,
            "tenant_id": principal["tenant_id"],
            "owner_id":  principal["user_id"],
            "title":     title,
        })

        logger.info(
            "report_created",
            extra={"report_id": report_id, "tenant_id": principal["tenant_id"]},
        )
        return _ok({"report_id": report_id, "created_at": now})

    # ------------------------------------------------------------------
    # get_report
    # ------------------------------------------------------------------

    @_handle_errors
    def get_report(self, request: dict, report_id: str) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:read")

        report_id = validate_uuid(report_id, "report_id")

        # Ownership predicate in the query (rules/03 §2)
        row = db.execute(
            """
            SELECT id, title, body, created_at, updated_at
              FROM reports
             WHERE id        = ?
               AND tenant_id = ?
               AND owner_id  = ?
            """,
            (report_id, principal["tenant_id"], principal["user_id"]),
        ).fetchone()

        if row is None:
            # 404 regardless of whether the report exists but belongs to
            # another user (rules/03 §2: don't leak existence via 403 vs 404)
            return _err(404, "Report not found")

        return _ok(dict(row))

    # ------------------------------------------------------------------
    # list_reports
    # ------------------------------------------------------------------

    @_handle_errors
    def list_reports(self, request: dict) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:read")

        rows = db.execute(
            """
            SELECT r.id, r.title, r.created_at, r.updated_at
              FROM reports r
             WHERE r.tenant_id = ?
               AND r.owner_id  = ?
             ORDER BY r.created_at DESC
            """,
            (principal["tenant_id"], principal["user_id"]),
        ).fetchall()

        return _ok({"reports": [dict(r) for r in rows]})

    # ------------------------------------------------------------------
    # search_reports
    # ------------------------------------------------------------------

    @_handle_errors
    def search_reports(self, request: dict) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:read")

        query_params = request.get("query") or {}

        q = validate_search_query(query_params.get("q", ""), "q")
        sort_col = validate_sort(query_params.get("sort", "created_at"))

        # LIKE value: escape % and _ so the user cannot widen the match
        # (rules/01 §2: LIKE wildcard escaping).
        like_val = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{like_val}%"

        # sort_col is a validated SQL column expression from SORT_COLUMNS;
        # it is interpolated into a fixed template, not user input.
        sql = f"""
            SELECT r.id, r.title, r.created_at, r.updated_at
              FROM reports r
             WHERE r.tenant_id = ?
               AND r.owner_id  = ?
               AND r.title LIKE ? ESCAPE '\\'
             ORDER BY {sort_col} DESC
        """  # noqa: S608 — sort_col is allowlist-validated, not user input

        rows = db.execute(
            sql,
            (principal["tenant_id"], principal["user_id"], like_pattern),
        ).fetchall()

        return _ok({"reports": [dict(r) for r in rows]})

    # ------------------------------------------------------------------
    # delete_report
    # ------------------------------------------------------------------

    @_handle_errors
    def delete_report(self, request: dict, report_id: str) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:delete")

        report_id = validate_uuid(report_id, "report_id")

        # Ownership predicate: admins can only delete their own reports
        # unless the spec is extended.  The current spec gives report:delete
        # to admins but does not grant cross-user deletion.
        cursor = db.execute(
            """
            DELETE FROM reports
             WHERE id        = ?
               AND tenant_id = ?
               AND owner_id  = ?
            """,
            (report_id, principal["tenant_id"], principal["user_id"]),
        )

        if cursor.rowcount == 0:
            return _err(404, "Report not found")

        audit_log(
            db,
            "report.deleted",
            actor_id=principal["user_id"],
            tenant_id=principal["tenant_id"],
            target_id=report_id,
        )
        db.commit()

        dispatch("report.deleted", {
            "report_id": report_id,
            "tenant_id": principal["tenant_id"],
            "actor_id":  principal["user_id"],
        })

        logger.info(
            "report_deleted",
            extra={"report_id": report_id, "tenant_id": principal["tenant_id"]},
        )
        return _ok({"deleted": True})

    # ------------------------------------------------------------------
    # upload_attachment
    # ------------------------------------------------------------------

    @_handle_errors
    def upload_attachment(self, request: dict) -> dict:
        db = self._db
        principal = authenticate(db, request)
        _rate_check(principal)
        require_permission(db, principal, "report:write")

        body = request.get("body") or {}

        filename  = validate_filename(body.get("filename", ""), "filename")
        mime_type = validate_mime_type(body.get("mime_type", ""), "mime_type")
        data_raw  = body.get("data")        # bytes in real HTTP; bytes here

        if not isinstance(data_raw, (bytes, bytearray)):
            return _err(400, "body.data must be bytes")

        data = bytes(data_raw)
        size = len(data)

        if size == 0:
            return _err(400, "Attachment must not be empty")
        if size > MAX_ATTACHMENT_BYTES:
            return _err(413, f"Attachment exceeds {MAX_ATTACHMENT_BYTES} bytes")

        # Scan before storing (rules/21 §1)
        if not scan(data, filename):
            logger.warning(
                "attachment_rejected_by_scanner",
                extra={"tenant_id": principal["tenant_id"], "size": size},
            )
            return _err(422, "Attachment rejected by content scanner")

        # Optional: link to a report
        report_id = body.get("report_id")
        if report_id is not None:
            report_id = validate_uuid(report_id, "report_id")
            # Verify the report belongs to this user/tenant (rules/03 §2)
            row = db.execute(
                "SELECT id FROM reports WHERE id=? AND tenant_id=? AND owner_id=?",
                (report_id, principal["tenant_id"], principal["user_id"]),
            ).fetchone()
            if row is None:
                return _err(404, "Report not found")

        # Storage key is a server-generated UUID; never user-controlled
        # (rules/01 §4: user input not used as path)
        storage_key = _new_id()
        attachment_id = _new_id()
        now = _now()

        db.execute(
            """
            INSERT INTO attachments(id, tenant_id, owner_id, report_id,
                                    filename, storage_key, size_bytes,
                                    mime_type, scan_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'clean', ?)
            """,
            (
                attachment_id,
                principal["tenant_id"],
                principal["user_id"],
                report_id,
                filename,
                storage_key,
                size,
                mime_type,
                now,
            ),
        )
        audit_log(
            db,
            "attachment.uploaded",
            actor_id=principal["user_id"],
            tenant_id=principal["tenant_id"],
            target_id=attachment_id,
            detail={"size_bytes": size, "mime_type": mime_type},
        )
        db.commit()

        logger.info(
            "attachment_uploaded",
            extra={
                "attachment_id": attachment_id,
                "tenant_id":     principal["tenant_id"],
                "size":          size,
            },
        )
        return _ok({"attachment_id": attachment_id, "storage_key": storage_key})

    # ------------------------------------------------------------------
    # handle_billing_webhook
    # ------------------------------------------------------------------

    @_handle_errors
    def handle_billing_webhook(self, request: dict) -> dict:
        """
        Process an ``invoice.paid`` event from the billing provider.

        Authentication: HMAC-SHA-256 over the raw body (rules/02 §8).
        Idempotency: event_id stored in billing_events; duplicate deliveries
        are silently accepted (the provider retries on non-2xx).
        """
        import os

        raw_body: bytes = request.get("raw_body", b"")
        headers = request.get("headers") or {}

        # Parse the Stripe-style signature header:
        #   X-Webhook-Signature: t=<unix>,v1=<hex_hmac>
        sig_header = headers.get("X-Webhook-Signature", "")
        timestamp = ""
        signature = ""
        for part in sig_header.split(","):
            if part.startswith("t="):
                timestamp = part[2:]
            elif part.startswith("v1="):
                signature = part[3:]

        secret_str = os.environ.get("BILLING_WEBHOOK_SECRET", "")
        if not secret_str:
            logger.error("billing_webhook_secret_not_configured")
            return _err(500, "Webhook secret not configured")

        secret = secret_str.encode()

        # Verify HMAC before parsing (rules/02 §8: authenticate before acting)
        if not verify_webhook_hmac(secret, raw_body, signature, timestamp):
            logger.warning("billing_webhook_signature_invalid")
            return _err(400, "Invalid webhook signature")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _err(400, "Invalid JSON body")

        event_type = payload.get("type")
        if event_type != "invoice.paid":
            # Unknown event types are acknowledged and ignored
            return _ok({"ignored": True})

        event_id  = str(payload.get("id", ""))
        tenant_id = str(payload.get("tenant_id", ""))
        amount    = payload.get("amount")
        currency  = str(payload.get("currency", ""))

        if not event_id or not tenant_id:
            return _err(400, "Missing event_id or tenant_id")
        if not isinstance(amount, int) or amount <= 0:
            return _err(400, "amount must be a positive integer (cents)")
        if not currency or len(currency) != 3:
            return _err(400, "currency must be a 3-letter ISO code")

        db = self._db

        # Idempotency check (the provider retries — rules/03 §3 one-time ops)
        existing = db.execute(
            "SELECT event_id FROM billing_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if existing:
            logger.info("billing_webhook_duplicate", extra={"event_id": event_id})
            return _ok({"duplicate": True})

        now = _now()
        db.execute(
            """
            INSERT INTO billing_events(event_id, tenant_id, amount, currency, processed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, amount, currency, now),
        )
        audit_log(
            db,
            "billing.invoice_paid",
            tenant_id=tenant_id,
            target_id=event_id,
            detail={"amount": amount, "currency": currency},
        )
        db.commit()

        logger.info(
            "billing_invoice_paid",
            extra={"event_id": event_id, "tenant_id": tenant_id},
        )
        return _ok({"processed": True})
