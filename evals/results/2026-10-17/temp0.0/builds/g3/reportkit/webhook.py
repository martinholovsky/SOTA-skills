"""
Billing webhook handler.

Verifies the HMAC-SHA256 signature over the raw body before any parsing.
Implements idempotency via the invoice_events table.

Security controls (rules/02 §8, rules/05 non-negotiables):
  - Signature verified constant-time over the raw body before parsing.
  - Timestamp window enforced to prevent replay.
  - Idempotency key stored to prevent double-processing on provider retries.
  - No secret or PII in logs.
"""

import hashlib
import hmac
import json
import sqlite3
import time
from typing import Any

from .audit import record as audit_record
from .config import Config
from .errors import BadRequest, Conflict, WebhookAuthFailed
from .logging import get_logger
from .validation import require_uuid, require_string

logger = get_logger(__name__)


def handle_billing_webhook(
    db: sqlite3.Connection,
    raw_body: bytes,
    signature_header: str,
    timestamp_header: str,
) -> dict[str, Any]:
    """
    Process an `invoice.paid` webhook from the billing provider.

    Parameters
    ----------
    db:
        Open database connection.
    raw_body:
        The exact bytes received from the provider (before any decoding).
    signature_header:
        Value of the provider's signature header (hex-encoded HMAC-SHA256).
    timestamp_header:
        Value of the provider's timestamp header (Unix epoch as a string).

    Returns a dict with the processing result.
    Raises WebhookAuthFailed, BadRequest, or Conflict on error.
    """
    # --- 1. Authenticate BEFORE parsing (rules/03 §1, rules/02 §8) ----------
    _verify_signature(raw_body, signature_header, timestamp_header)

    # --- 2. Parse only after auth -------------------------------------------
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BadRequest(f"Invalid JSON body: {exc}") from exc

    if not isinstance(payload, dict):
        raise BadRequest("Webhook body must be a JSON object")

    event_type = payload.get("type")
    if event_type != "invoice.paid":
        # Unknown event types are acknowledged but not processed.
        logger.info("webhook_ignored", extra={"event_type": event_type})
        return {"status": "ignored", "event_type": event_type}

    # --- 3. Validate fields --------------------------------------------------
    event_id = payload.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise BadRequest("'id' field is required and must be a non-empty string")
    # Length-cap the event_id (it's a provider-generated opaque string).
    if len(event_id) > 128:
        raise BadRequest("'id' field too long")

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise BadRequest("'data' must be an object")

    tenant_id = data.get("tenant_id")
    require_uuid(tenant_id, "tenant_id")

    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        raise BadRequest("'amount' must be a positive integer (cents)")

    currency = data.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        raise BadRequest("'currency' must be a 3-letter ISO 4217 code")
    currency = currency.upper()

    # --- 4. Idempotency: reject duplicate event_ids -------------------------
    existing = db.execute(
        "SELECT event_id FROM invoice_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    if existing is not None:
        logger.info("webhook_duplicate", extra={"event_id": event_id})
        return {"status": "duplicate", "event_id": event_id}

    # --- 5. Persist ----------------------------------------------------------
    db.execute(
        """
        INSERT INTO invoice_events (event_id, tenant_id, amount, currency)
        VALUES (?, ?, ?, ?)
        """,
        (event_id, tenant_id, amount, currency),
    )
    audit_record(
        db,
        action="billing.invoice_paid",
        tenant_id=tenant_id,
        detail={"event_id": event_id, "currency": currency},
        # amount deliberately omitted from audit detail to avoid financial PII
        # in the general audit log; it lives in invoice_events.
    )
    db.commit()

    logger.info(
        "webhook_processed",
        extra={"event_id": event_id, "tenant_id": tenant_id},
    )
    return {"status": "ok", "event_id": event_id}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _verify_signature(
    raw_body: bytes,
    signature_header: str,
    timestamp_header: str,
) -> None:
    """
    Verify HMAC-SHA256 signature and timestamp window.

    Raises WebhookAuthFailed on any failure.
    The error message is deliberately generic (no oracle).
    """
    secret = Config.BILLING_WEBHOOK_SECRET
    if not secret:
        logger.error("webhook_secret_not_configured")
        raise WebhookAuthFailed("Webhook authentication not configured")

    # Validate timestamp to prevent replay (rules/02 §8).
    try:
        ts = int(timestamp_header)
    except (ValueError, TypeError):
        raise WebhookAuthFailed("Invalid webhook request")

    now = int(time.time())
    if abs(now - ts) > Config.WEBHOOK_TIMESTAMP_TOLERANCE:
        logger.warning("webhook_replay_rejected", extra={"delta": abs(now - ts)})
        raise WebhookAuthFailed("Invalid webhook request")

    # Compute expected signature: HMAC-SHA256(secret, timestamp + "." + body).
    # The signed payload includes the timestamp so it cannot be replayed with
    # a different timestamp.
    signed_payload = f"{ts}.".encode() + raw_body
    expected = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()

    # Constant-time comparison (rules/02 §8).
    if not hmac.compare_digest(expected, signature_header.strip()):
        logger.warning("webhook_signature_mismatch")
        raise WebhookAuthFailed("Invalid webhook request")
