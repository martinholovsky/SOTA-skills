"""Billing webhook handler.

The provider POSTs signed `invoice.paid` events.  Requests are authenticated
with an HMAC-SHA256 signature over the raw request body; the shared secret is
read from the environment variable BILLING_WEBHOOK_SECRET.

Idempotency: the provider may retry deliveries it considers failed (non-2xx or
timeout).  We deduplicate on the provider's event id using a UNIQUE index on
billing_events.id, so a second delivery of the same event is a no-op (we
return 200 to stop retries).
"""

import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from .errors import ValidationError, WebhookSignatureError


def _secret() -> bytes:
    val = os.environ.get("BILLING_WEBHOOK_SECRET", "")
    if not val:
        raise RuntimeError("BILLING_WEBHOOK_SECRET is not set")
    return val.encode()


def _verify_signature(raw_body: bytes, signature_header: str) -> None:
    """Verify HMAC-SHA256(secret, raw_body) == signature_header.

    The provider sends the hex digest in the 'X-Billing-Signature' header.
    """
    expected = hmac.new(_secret(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header.lower()):
        raise WebhookSignatureError("Billing webhook signature mismatch")


def handle_webhook(conn: sqlite3.Connection, request: dict) -> dict:
    """Process an inbound billing webhook.

    request dict keys
    -----------------
    body_bytes  : bytes   — raw request body (used for signature verification)
    headers     : dict    — HTTP headers (must contain X-Billing-Signature)

    Returns a response dict with 'status' and 'body'.
    """
    raw_body: bytes = request.get("body_bytes") or b""
    headers: dict   = request.get("headers") or {}
    sig = headers.get("X-Billing-Signature") or headers.get("x-billing-signature") or ""

    if not sig:
        raise WebhookSignatureError("Missing X-Billing-Signature header")

    _verify_signature(raw_body, sig)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in webhook body: {exc}") from exc

    event_type  = payload.get("type", "")
    event_id    = payload.get("id") or str(uuid.uuid4())
    tenant_id   = payload.get("tenant_id", "")
    amount_cents = int(payload.get("amount_cents", 0))

    if event_type != "invoice.paid":
        # Unknown event types are acknowledged but not processed.
        return {"status": 200, "body": {"acknowledged": True, "processed": False}}

    if not tenant_id:
        raise ValidationError("invoice.paid event missing tenant_id")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    try:
        conn.execute(
            """
            INSERT INTO billing_events (id, tenant_id, event_type, amount_cents, payload, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, event_type, amount_cents, raw_body.decode(errors="replace"), now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Duplicate delivery — idempotent, return 200 to stop retries.
        return {"status": 200, "body": {"acknowledged": True, "processed": False, "duplicate": True}}

    return {"status": 200, "body": {"acknowledged": True, "processed": True}}
