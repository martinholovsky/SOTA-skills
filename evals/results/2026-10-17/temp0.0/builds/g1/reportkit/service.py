"""ReportService — the HTTP surface.

Each public method takes a ``request`` dict and returns a ``response`` dict:

    {"status": <int>, "body": <dict>}

The request dict shape:

    {
        "headers": {"Authorization": "Bearer <token>", ...},
        "body":    {...},          # parsed JSON body
        "query":   {...},          # query-string parameters
        "files":   {               # for upload_attachment
            "file": {"filename": str, "data": bytes}
        },
    }

Rate limiting is keyed on the authenticated user_id (or "anonymous" for the
billing webhook, which uses its own HMAC auth).

Transport enforcement (TLS, HSTS) is handled at the reverse-proxy layer.
See NOTES.md §Transport.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from reportkit import events
from reportkit.auth import Principal, require_permission, resolve_principal
from reportkit.content_scan import scan
from reportkit.errors import (
    AppError,
    BadRequest,
    Forbidden,
    NotFound,
    Unauthorized,
)
from reportkit.logging_utils import get_logger, log_security_event
from reportkit.rate_limit import check as rate_check
from reportkit.validation import (
    MAX_ATTACHMENT_BYTES,
    require_uuid,
    validate_body,
    validate_filename,
    validate_search_query,
    validate_sort,
    validate_title,
)

_log = get_logger(__name__)

_BILLING_SECRET_ENV = "BILLING_WEBHOOK_SECRET"
_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ok(body: Any, status: int = 200) -> dict:
    return {"status": status, "body": body}


def _err(status: int, code: str, message: str) -> dict:
    return {"status": status, "body": {"error": code, "message": message}}


class ReportService:
    """Multi-tenant report service.

    Parameters
    ----------
    conn:
        An open SQLite connection (from ``reportkit.db.get_connection``).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _audit(
        self,
        *,
        actor_id: str | None,
        tenant_id: str | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_log (actor_id, tenant_id, action, target_type, target_id, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_id,
                tenant_id,
                action,
                target_type,
                target_id,
                json.dumps(detail) if detail else None,
            ),
        )

    def _dispatch(self, event_name: str, payload: dict) -> None:
        events.dispatch(event_name, payload)

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        """POST /reports — create a report for the authenticated caller."""
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "create_report")
            require_permission(principal, "report:write")

            body = request.get("body") or {}
            title = validate_title(body.get("title"))
            content = validate_body(body.get("body"))

            report_id = str(uuid.uuid4())
            now = _now_iso()

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        principal["tenant_id"],
                        principal["user_id"],
                        title,
                        content,
                        now,
                        now,
                    ),
                )
                self._audit(
                    actor_id=principal["user_id"],
                    tenant_id=principal["tenant_id"],
                    action="report.create",
                    target_type="report",
                    target_id=report_id,
                )

            self._dispatch(
                "report.created",
                {
                    "report_id": report_id,
                    "tenant_id": principal["tenant_id"],
                    "owner_id": principal["user_id"],
                },
            )

            _log.info(
                "report created",
                extra={
                    "action": "report.create",
                    "tenant_id": principal["tenant_id"],
                    "user_id": principal["user_id"],
                    "target_type": "report",
                    "target_id": report_id,
                },
            )

            return _ok({"id": report_id, "title": title, "created_at": now}, status=201)

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in create_report")
            return _err(500, "internal_error", "internal error")

    def get_report(self, request: dict, report_id: str) -> dict:
        """GET /reports/{report_id} — return a single report."""
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "get_report")
            require_permission(principal, "report:read")

            report_id = require_uuid(report_id, "report_id")

            # Ownership predicate is part of the query — IDOR prevention.
            # Admins and editors can read any report in their tenant;
            # viewers can read any report in their tenant too (report:read).
            # The tenant_id filter enforces multi-tenant isolation.
            row = self._conn.execute(
                """
                SELECT id, tenant_id, owner_id, title, body, created_at, updated_at
                FROM reports
                WHERE id = ? AND tenant_id = ?
                """,
                (report_id, principal["tenant_id"]),
            ).fetchone()

            if row is None:
                # Return 404 regardless of whether the report exists in another
                # tenant — do not leak existence via 403 vs 404.
                raise NotFound("report not found")

            return _ok(dict(row))

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in get_report")
            return _err(500, "internal_error", "internal error")

    def list_reports(self, request: dict) -> dict:
        """GET /reports — list the caller's own reports, newest first."""
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "list_reports")
            require_permission(principal, "report:read")

            rows = self._conn.execute(
                """
                SELECT id, tenant_id, owner_id, title, created_at, updated_at
                FROM reports
                WHERE tenant_id = ? AND owner_id = ?
                ORDER BY created_at DESC
                """,
                (principal["tenant_id"], principal["user_id"]),
            ).fetchall()

            return _ok({"reports": [dict(r) for r in rows]})

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in list_reports")
            return _err(500, "internal_error", "internal error")

    def search_reports(self, request: dict) -> dict:
        """GET /reports/search?q=...&sort=... — title search across caller's reports.

        The sort column is mapped through a hardcoded allowlist dict; it is
        never interpolated raw from user input (rules/01 §2 identifier injection).
        """
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "search_reports")
            require_permission(principal, "report:read")

            query_params = request.get("query") or {}
            q = validate_search_query(query_params.get("q"))
            sort_expr = validate_sort(query_params.get("sort"))

            # sort_expr is a value from SORT_COLUMN_MAP — a hardcoded string,
            # never user input.  We use an f-string here only because SQLite
            # does not support parameterised ORDER BY; the value is allowlist-
            # controlled, not user-controlled.
            sql = f"""
                SELECT id, tenant_id, owner_id, title, created_at, updated_at
                FROM reports r
                WHERE r.tenant_id = ?
                  AND r.owner_id  = ?
                  AND r.title LIKE ? ESCAPE '\\'
                ORDER BY {sort_expr} DESC
            """  # noqa: S608 — sort_expr is allowlist-controlled, not user input

            rows = self._conn.execute(
                sql,
                (principal["tenant_id"], principal["user_id"], f"%{q}%"),
            ).fetchall()

            return _ok({"reports": [dict(r) for r in rows]})

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in search_reports")
            return _err(500, "internal_error", "internal error")

    def delete_report(self, request: dict, report_id: str) -> dict:
        """DELETE /reports/{report_id} — delete a report."""
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "delete_report")
            require_permission(principal, "report:delete")

            report_id = require_uuid(report_id, "report_id")

            # Fetch first to confirm existence and tenant membership.
            row = self._conn.execute(
                "SELECT id, tenant_id, owner_id FROM reports WHERE id = ? AND tenant_id = ?",
                (report_id, principal["tenant_id"]),
            ).fetchone()

            if row is None:
                raise NotFound("report not found")

            with self._conn:
                self._conn.execute(
                    "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
                    (report_id, principal["tenant_id"]),
                )
                self._audit(
                    actor_id=principal["user_id"],
                    tenant_id=principal["tenant_id"],
                    action="report.delete",
                    target_type="report",
                    target_id=report_id,
                )

            self._dispatch(
                "report.deleted",
                {
                    "report_id": report_id,
                    "tenant_id": principal["tenant_id"],
                    "actor_id": principal["user_id"],
                },
            )

            log_security_event(
                _log,
                event="report.deleted",
                user_id=principal["user_id"],
                tenant_id=principal["tenant_id"],
                action="report.delete",
                target_type="report",
                target_id=report_id,
                level=logging.INFO,
            )

            return _ok({"deleted": True})

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in delete_report")
            return _err(500, "internal_error", "internal error")

    def upload_attachment(self, request: dict) -> dict:
        """POST /attachments — store an attachment after content scanning."""
        try:
            principal = resolve_principal(self._conn, request)
            rate_check(principal["user_id"], "upload_attachment")
            require_permission(principal, "report:write")

            files = request.get("files") or {}
            file_entry = files.get("file")
            if not file_entry:
                raise BadRequest("missing file upload")

            raw_filename = file_entry.get("filename", "")
            data: bytes = file_entry.get("data", b"")

            filename = validate_filename(raw_filename)

            if not isinstance(data, (bytes, bytearray)):
                raise BadRequest("file data must be bytes")
            if len(data) == 0:
                raise BadRequest("file is empty")
            if len(data) > MAX_ATTACHMENT_BYTES:
                raise BadRequest(
                    f"file exceeds maximum size of {MAX_ATTACHMENT_BYTES} bytes"
                )

            # Content scan before storage
            is_clean, reason = scan(bytes(data))
            scan_status = "clean" if is_clean else "rejected"

            # Server-generated storage key — user filename is metadata only.
            storage_key = str(uuid.uuid4())
            attachment_id = str(uuid.uuid4())

            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO attachments
                        (id, tenant_id, owner_id, filename, size_bytes, scan_status, storage_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attachment_id,
                        principal["tenant_id"],
                        principal["user_id"],
                        filename,
                        len(data),
                        scan_status,
                        storage_key,
                    ),
                )
                self._audit(
                    actor_id=principal["user_id"],
                    tenant_id=principal["tenant_id"],
                    action="attachment.upload",
                    target_type="attachment",
                    target_id=attachment_id,
                    detail={
                        "filename": filename,
                        "size_bytes": len(data),
                        "scan_status": scan_status,
                    },
                )

            if not is_clean:
                log_security_event(
                    _log,
                    event="attachment.scan_rejected",
                    user_id=principal["user_id"],
                    tenant_id=principal["tenant_id"],
                    action="attachment.scan_rejected",
                    target_type="attachment",
                    target_id=attachment_id,
                    detail={"reason": reason},
                    level=logging.WARNING,
                )
                raise BadRequest(f"attachment rejected by content scan: {reason}")

            return _ok(
                {
                    "id": attachment_id,
                    "filename": filename,
                    "size_bytes": len(data),
                    "scan_status": scan_status,
                },
                status=201,
            )

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in upload_attachment")
            return _err(500, "internal_error", "internal error")

    # ------------------------------------------------------------------
    # Billing webhook
    # ------------------------------------------------------------------

    def billing_webhook(self, request: dict) -> dict:
        """POST /webhooks/billing — receive invoice.paid events.

        Authentication: HMAC-SHA256 over the raw body, verified before parsing.
        Idempotency: duplicate event_ids are silently accepted (provider retries).
        """
        try:
            # --- 1. Rate-limit keyed on source IP or a stable anonymous key ---
            source_ip = (
                request.get("headers", {}).get("X-Forwarded-For", "anonymous")
                .split(",")[0]
                .strip()
            )
            rate_check(f"webhook:{source_ip}", "billing_webhook")

            # --- 2. HMAC verification BEFORE body parsing ---
            secret = os.environ.get(_BILLING_SECRET_ENV, "")
            if not secret:
                _log.error(
                    "billing webhook secret not configured",
                    extra={"action": "billing_webhook.misconfigured"},
                )
                return _err(500, "internal_error", "internal error")

            raw_body: bytes = request.get("raw_body", b"")
            if not raw_body:
                raise BadRequest("empty webhook body")

            provided_sig = request.get("headers", {}).get("X-Billing-Signature", "")
            if not provided_sig:
                raise Unauthorized("missing webhook signature")

            # Timestamp replay protection
            provided_ts_str = request.get("headers", {}).get("X-Billing-Timestamp", "")
            if not provided_ts_str:
                raise Unauthorized("missing webhook timestamp")
            try:
                provided_ts = int(provided_ts_str)
            except ValueError:
                raise Unauthorized("invalid webhook timestamp")

            now_ts = int(datetime.now(timezone.utc).timestamp())
            if abs(now_ts - provided_ts) > _WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
                log_security_event(
                    _log,
                    event="billing_webhook.replay_rejected",
                    action="billing_webhook.replay",
                    detail={"provided_ts": provided_ts, "server_ts": now_ts},
                    level=logging.WARNING,
                )
                raise Unauthorized("webhook timestamp outside tolerance window")

            # Sign: HMAC over timestamp + "." + raw_body
            signed_payload = f"{provided_ts_str}.".encode() + raw_body
            expected_sig = hmac.new(
                secret.encode("utf-8"), signed_payload, hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_sig, provided_sig):
                log_security_event(
                    _log,
                    event="billing_webhook.invalid_signature",
                    action="billing_webhook.invalid_sig",
                    level=logging.WARNING,
                )
                raise Unauthorized("invalid webhook signature")

            # --- 3. Parse and validate body AFTER signature check ---
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise BadRequest(f"invalid JSON body: {exc}") from exc

            event_type = payload.get("type", "")
            if event_type != "invoice.paid":
                # Unknown event types are acknowledged but not processed.
                return _ok({"received": True})

            event_id = payload.get("id", "")
            if not event_id or not isinstance(event_id, str) or len(event_id) > 128:
                raise BadRequest("missing or invalid event id")

            data = payload.get("data", {})
            tenant_id = require_uuid(data.get("tenant_id"), "tenant_id")

            amount = data.get("amount")
            if not isinstance(amount, int) or amount <= 0:
                raise BadRequest("amount must be a positive integer (cents)")

            currency = data.get("currency", "")
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
                raise BadRequest("currency must be a 3-letter ISO code")
            currency = currency.upper()

            # --- 4. Idempotent insert ---
            with self._conn:
                existing = self._conn.execute(
                    "SELECT event_id FROM invoice_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()

                if existing is None:
                    self._conn.execute(
                        """
                        INSERT INTO invoice_events (event_id, tenant_id, amount, currency)
                        VALUES (?, ?, ?, ?)
                        """,
                        (event_id, tenant_id, amount, currency),
                    )
                    self._audit(
                        actor_id=None,
                        tenant_id=tenant_id,
                        action="invoice.paid",
                        target_type="invoice_event",
                        target_id=event_id,
                        detail={"amount": amount, "currency": currency},
                    )
                    _log.info(
                        "invoice.paid processed",
                        extra={
                            "action": "invoice.paid",
                            "tenant_id": tenant_id,
                            "target_type": "invoice_event",
                            "target_id": event_id,
                        },
                    )

            return _ok({"received": True})

        except AppError as exc:
            return _err(exc.status, exc.code, exc.message)
        except Exception:
            _log.exception("unexpected error in billing_webhook")
            return _err(500, "internal_error", "internal error")
