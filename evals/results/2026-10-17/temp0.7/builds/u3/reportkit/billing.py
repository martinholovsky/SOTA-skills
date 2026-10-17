"""Billing webhook handler.

Verifies the HMAC signature supplied by the billing provider and records
the payment in the ledger.  The provider retries deliveries it considers
failed, so we use the event_id as an idempotency key.
"""
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from .auth import AuthError


class BillingError(Exception):
    """Non-auth billing processing error."""


def _verify_signature(raw_body: bytes, signature_header: str, secret: str) -> None:
    """Verify HMAC-SHA256 signature.

    The provider sends  'sha256=<hex_digest>'  in the X-Billing-Signature header.
    """
    if not signature_header:
        raise AuthError("Missing billing signature header")
    parts = signature_header.split("=", 1)
    if len(parts) != 2 or parts[0] != "sha256":
        raise AuthError("Malformed billing signature header")
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, parts[1]):
        raise AuthError("Billing signature verification failed")


def handle_webhook(
    conn: sqlite3.Connection,
    raw_body: bytes,
    signature_header: str,
    secret: str | None = None,
) -> dict:
    """Process a billing webhook delivery.

    Returns a dict describing what was recorded (or skipped as duplicate).
    Raises AuthError on bad signature, BillingError on bad payload.
    """
    if secret is None:
        secret = os.environ.get("BILLING_WEBHOOK_SECRET", "")
    if not secret:
        raise BillingError("BILLING_WEBHOOK_SECRET is not configured")

    _verify_signature(raw_body, signature_header, secret)

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise BillingError(f"Invalid JSON in webhook body: {exc}") from exc

    if event.get("type") != "invoice.paid":
        # Acknowledge but ignore other event types
        return {"status": "ignored", "type": event.get("type")}

    event_id  = event.get("id")
    tenant_id = event.get("tenant_id")
    invoice_id = event.get("data", {}).get("invoice_id")
    amount_cents = event.get("data", {}).get("amount_cents")
    currency = event.get("data", {}).get("currency", "usd")

    if not all([event_id, tenant_id, invoice_id, amount_cents is not None]):
        raise BillingError("Webhook payload missing required fields")

    # Idempotency: if we've already recorded this event_id, return success
    existing = conn.execute(
        "SELECT id FROM billing_ledger WHERE event_id = ?", (event_id,)
    ).fetchone()
    if existing:
        return {"status": "duplicate", "event_id": event_id}

    ledger_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
    conn.execute(
        """
        INSERT INTO billing_ledger
            (id, tenant_id, invoice_id, amount_cents, currency, event_id, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ledger_id, tenant_id, invoice_id, amount_cents, currency, event_id, now),
    )
    conn.commit()
    return {"status": "recorded", "ledger_id": ledger_id, "event_id": event_id}
