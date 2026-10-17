"""
ReportService — the HTTP surface.

Each public method accepts a *request* dict and returns a *response* dict:
    {"status": <int>, "body": <dict>}

The request dict shape:
    {
        "headers":  {"Authorization": "Bearer <token>", ...},
        "query":    {"sort": "created_at", ...},
        "body":     {...},               # parsed JSON / form data
        "raw_body": b"...",              # bytes, for HMAC verification
    }

Rate limiting, authentication, and authorisation are applied at the top of
every handler before any DB work.  A failed check ends the handler
immediately (no fall-through).

Transport (TLS/HSTS) is enforced at the reverse-proxy layer; see NOTES.md.
"""

import hashlib
import hmac
import json
import logging
import os
import uuid
from typing import Any

from .auth      import AuthError, resolve_principal
from .db        import get_connection
from .events    import dispatch
from .ops       import purge_tenant, set_role          # re-exported for convenience
from .rate_limit import RateLimitExceeded, check_rate_limit
from .scanner   import scan
from .validation import (
    MAX_BODY_LEN,
    MAX_SEARCH_LEN,
    MAX_TITLE_LEN,
    ValidationError,
    validate_content_type,
    validate_filename,
    validate_attachment_size,
    validate_sort_key,
    require_string,
    require_uuid,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _ok(body: Any = None, status: int = 200) -> dict:
    return {"status": status, "body": body or {}}


def _err(message: str, status: int) -> dict:
    return {"status": status, "body": {"error": message}}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ReportService:
    """
    Multi-tenant report service.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.
    billing_secret:
        Raw bytes of the HMAC-SHA256 shared secret used to verify billing
        webhook payloads.  Defaults to the BILLING_SECRET environment
        variable (hex-decoded).
    attachment_store:
        Callable(storage_key: str, data: bytes) -> None.  Defaults to a
        local-filesystem store under ``./attachments/``.
    """

    def __init__(
        self,
        db_path: str,
        *,
        billing_secret: bytes | None = None,
        attachment_store=None,
    ) -> None:
        self._db_path = db_path
        self._billing_secret: bytes = billing_secret or bytes.fromhex(
            os.environ.get("BILLING_SECRET", "")
        )
        self._attachment_store = attachment_store or _default_attachment_store

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self):
        return get_connection(self._db_path)

    def _authenticate(self, request: dict):
        """Resolve the bearer token; raise AuthError on failure."""
        return resolve_principal(request, self._conn())

    def _rate_limit(self, caller_id: str, endpoint: str) -> None:
        check_rate_limit(self._conn(), caller_id, endpoint)

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "create_report")
            principal.require("report:write")

            body = request.get("body") or {}
            title = require_string(body.get("title", ""), "title", max_len=MAX_TITLE_LEN)
            rpt_body = require_string(
                body.get("body", ""), "body",
                max_len=MAX_BODY_LEN, min_len=0,
            )

            report_id = str(uuid.uuid4())
            with conn:
                conn.execute(
                    """
                    INSERT INTO reports (id, tenant_id, owner_id, title, body)
                         VALUES (?, ?, ?, ?, ?)
                    """,
                    (report_id, principal.tenant_id, principal.user_id, title, rpt_body),
                )

            dispatch("report.created", {
                "report_id": report_id,
                "tenant_id": principal.tenant_id,
            })

            logger.info(
                "report.create",
                extra={
                    "report_id": report_id,
                    "tenant_id": principal.tenant_id,
                    "user_id":   principal.user_id,
                },
            )
            return _ok({"report_id": report_id}, status=201)

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)
        except ValidationError as exc:
            return _err(str(exc), 400)

    def get_report(self, request: dict, report_id: str) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "get_report")
            principal.require("report:read")

            # Validate the supplied ID before touching the DB.
            report_id = require_uuid(report_id, "report_id")

            row = conn.execute(
                """
                SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
                  FROM reports
                 WHERE id        = ?
                   AND tenant_id = ?
                """,
                (report_id, principal.tenant_id),
            ).fetchone()

            # Return 404 regardless of whether the report exists in another
            # tenant (do not leak existence via 403 vs 404).
            if row is None:
                return _err("not found", 404)

            return _ok(_row_to_report(row))

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)
        except ValidationError as exc:
            return _err(str(exc), 400)

    def list_reports(self, request: dict) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "list_reports")
            principal.require("report:read")

            rows = conn.execute(
                """
                SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
                  FROM reports
                 WHERE tenant_id = ?
                   AND owner_id  = ?
                 ORDER BY created_at DESC
                """,
                (principal.tenant_id, principal.user_id),
            ).fetchall()

            return _ok({"reports": [_row_to_report(r) for r in rows]})

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)

    def search_reports(self, request: dict) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "search_reports")
            principal.require("report:read")

            query_params = request.get("query") or {}

            # Validate and sanitise the search term.
            raw_q = query_params.get("q", "")
            q = require_string(raw_q, "q", max_len=MAX_SEARCH_LEN, min_len=1)

            # Map the user's sort choice through the allowlist.
            raw_sort = query_params.get("sort", "created_at")
            sort_col = validate_sort_key(raw_sort)

            # Escape LIKE metacharacters in the search term so the user
            # cannot control match breadth.
            escaped_q = _escape_like(q)

            rows = conn.execute(
                # sort_col comes from the allowlist dict, not from user input.
                f"""
                SELECT r.id, r.tenant_id, r.owner_id, r.title, r.body,
                       r.created_at, r.updated_at
                  FROM reports r
                 WHERE r.tenant_id = ?
                   AND r.owner_id  = ?
                   AND r.title LIKE ? ESCAPE '\\'
                 ORDER BY {sort_col} ASC
                """,
                (principal.tenant_id, principal.user_id, f"%{escaped_q}%"),
            ).fetchall()

            return _ok({"reports": [_row_to_report(r) for r in rows]})

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)
        except ValidationError as exc:
            return _err(str(exc), 400)

    def delete_report(self, request: dict, report_id: str) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "delete_report")
            principal.require("report:delete")

            report_id = require_uuid(report_id, "report_id")

            with conn:
                cursor = conn.execute(
                    """
                    DELETE FROM reports
                     WHERE id        = ?
                       AND tenant_id = ?
                    """,
                    (report_id, principal.tenant_id),
                )

            if cursor.rowcount == 0:
                return _err("not found", 404)

            dispatch("report.deleted", {
                "report_id": report_id,
                "tenant_id": principal.tenant_id,
            })

            logger.info(
                "report.delete",
                extra={
                    "report_id": report_id,
                    "tenant_id": principal.tenant_id,
                    "user_id":   principal.user_id,
                },
            )
            return _ok(status=204)

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)
        except ValidationError as exc:
            return _err(str(exc), 400)

    def upload_attachment(self, request: dict) -> dict:
        conn = self._conn()
        try:
            principal = self._authenticate(request)
            self._rate_limit(principal.user_id, "upload_attachment")
            principal.require("report:write")

            body = request.get("body") or {}

            report_id    = require_uuid(body.get("report_id", ""), "report_id")
            filename     = validate_filename(body.get("filename", ""))
            content_type = validate_content_type(body.get("content_type", ""))
            file_data: bytes = body.get("data", b"")

            if not isinstance(file_data, (bytes, bytearray)):
                raise ValidationError("data: must be bytes", "data")
            validate_attachment_size(len(file_data))

            # Verify the report exists and belongs to this tenant/owner.
            row = conn.execute(
                "SELECT id FROM reports WHERE id = ? AND tenant_id = ?",
                (report_id, principal.tenant_id),
            ).fetchone()
            if row is None:
                return _err("report not found", 404)

            # Scan before storing.
            result = scan(bytes(file_data))
            scan_status = "clean" if result.clean else "flagged"
            if not result.clean:
                logger.warning(
                    "attachment.scan_flagged",
                    extra={
                        "tenant_id": principal.tenant_id,
                        "reason":    result.reason,
                        # filename omitted: may contain PII
                    },
                )
                return _err(f"attachment rejected: {result.reason}", 422)

            # Storage key is a server-generated UUID — never derived from
            # user-supplied filename or path.
            storage_key = str(uuid.uuid4())

            self._attachment_store(storage_key, bytes(file_data))

            attachment_id = str(uuid.uuid4())
            with conn:
                conn.execute(
                    """
                    INSERT INTO attachments
                           (id, report_id, tenant_id, filename, storage_key,
                            size_bytes, content_type, scan_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attachment_id,
                        report_id,
                        principal.tenant_id,
                        filename,
                        storage_key,
                        len(file_data),
                        content_type,
                        scan_status,
                    ),
                )

            logger.info(
                "attachment.upload",
                extra={
                    "attachment_id": attachment_id,
                    "report_id":     report_id,
                    "tenant_id":     principal.tenant_id,
                    "size_bytes":    len(file_data),
                    "content_type":  content_type,
                    # filename not logged (may contain PII)
                },
            )
            return _ok({"attachment_id": attachment_id}, status=201)

        except (AuthError, RateLimitExceeded) as exc:
            return _err(str(exc), exc.status)
        except ValidationError as exc:
            return _err(str(exc), 400)

    def billing_webhook(self, request: dict) -> dict:
        """
        Receive an ``invoice.paid`` event from the billing provider.

        Authentication: HMAC-SHA256 over the raw request body, provided in
        the ``X-Billing-Signature`` header as a hex digest.

        Idempotency: the provider retries; we use the event id as an
        idempotency key stored in the ledger.
        """
        conn = self._conn()
        try:
            # Rate-limit by remote IP if present, else a fixed key.
            caller_id = request.get("remote_addr") or "billing_provider"
            self._rate_limit(caller_id, "billing_webhook")

            # --- Authentication: verify HMAC before parsing body ---
            sig_header = (
                request.get("headers", {}).get("X-Billing-Signature")
                or request.get("headers", {}).get("x-billing-signature")
                or ""
            )
            raw_body: bytes = request.get("raw_body", b"")

            if not sig_header:
                logger.warning("billing_webhook.missing_signature")
                return _err("missing signature", 401)

            if not self._billing_secret:
                logger.error("billing_webhook.no_secret_configured")
                return _err("server misconfiguration", 500)

            expected = hmac.new(
                self._billing_secret, raw_body, "sha256"
            ).hexdigest()
            if not hmac.compare_digest(expected, sig_header.lower()):
                logger.warning("billing_webhook.invalid_signature")
                return _err("invalid signature", 401)

            # --- Parse body (safe after signature verification) ---
            try:
                event = json.loads(raw_body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return _err("invalid JSON body", 400)

            event_type = event.get("type")
            if event_type != "invoice.paid":
                # Acknowledge unknown event types silently (do not error —
                # the provider may send other event types).
                return _ok({"received": True})

            event_id    = str(event.get("id", ""))
            tenant_id   = str(event.get("tenant_id", ""))
            invoice_id  = str(event.get("invoice_id", ""))
            amount_cents = event.get("amount_cents")

            if not event_id or not tenant_id or not invoice_id:
                return _err("missing required fields", 400)
            if not isinstance(amount_cents, int) or amount_cents <= 0:
                return _err("amount_cents must be a positive integer", 400)

            # Validate tenant exists.
            row = conn.execute(
                "SELECT id FROM tenants WHERE id = ?", (tenant_id,)
            ).fetchone()
            if row is None:
                return _err("tenant not found", 404)

            # Idempotent insert: duplicate event_id is silently accepted.
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO ledger_entries
                               (id, tenant_id, invoice_id, amount_cents, idempotency_key)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            tenant_id,
                            invoice_id,
                            amount_cents,
                            event_id,
                        ),
                    )
            except conn.execute.__self__.__class__.IntegrityError:
                # Duplicate idempotency_key — already processed.
                logger.info(
                    "billing_webhook.duplicate_event",
                    extra={"event_id": event_id, "tenant_id": tenant_id},
                )
                return _ok({"received": True, "duplicate": True})

            logger.info(
                "billing_webhook.processed",
                extra={
                    "event_id":     event_id,
                    "tenant_id":    tenant_id,
                    "invoice_id":   invoice_id,
                    "amount_cents": amount_cents,
                },
            )
            return _ok({"received": True})

        except RateLimitExceeded as exc:
            return _err(str(exc), exc.status)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_report(row) -> dict:
    return {
        "id":         row["id"],
        "tenant_id":  row["tenant_id"],
        "owner_id":   row["owner_id"],
        "title":      row["title"],
        "body":       row["body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters so user input cannot control match breadth."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _default_attachment_store(storage_key: str, data: bytes) -> None:
    """
    Default attachment storage: write to ./attachments/<uuid>.

    In production, replace with an object-storage backend.
    The storage_key is always a server-generated UUID, never user-supplied.
    """
    import pathlib
    store_dir = pathlib.Path("attachments")
    store_dir.mkdir(exist_ok=True)
    # storage_key is a UUID (validated at generation site); safe to use as filename.
    dest = store_dir / storage_key
    dest.write_bytes(data)
