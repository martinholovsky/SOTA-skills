"""
Billing webhook handler.

Verifies the HMAC-SHA256 signature supplied by the billing provider, then
applies the payment to the ledger.  The shared secret is read from the
environment variable BILLING_WEBHOOK_SECRET.

Idempotency: the provider retries deliveries it considers failed.  We use the
event's idempotency_key (derived from the provider's event ID) as a UNIQUE
constraint in the ledger table; a duplicate delivery returns 200 without
re-inserting.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import uuid
import logging

logger = logging.getLogger(__name__)

_SECRET_ENV_VAR = "BILLING_WEBHOOK_SECRET"


class WebhookAuthError(Exception):
    """Raised when the HMAC signature on a webhook request is invalid."""


def _get_secret() -> bytes:
    secret = os.environ.get(_SECRET_ENV_VAR, "")
    if not secret:
        raise EnvironmentError(
            f"Environment variable {_SECRET_ENV_VAR!r} is not set."
        )
    return secret.encode()


def verify_signature(raw_body: bytes, signature_header: str) -> None:
    """
    Verify the HMAC-SHA256 signature sent by the billing provider.

    The provider sends:  X-Billing-Signature: sha256=<hex-digest>
    """
    if not signature_header.startswith("sha256="):
        raise WebhookAuthError("Signature header must start with 'sha256='.")
    expected_hex = signature_header[7:]
    secret = _get_secret()
    computed = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, expected_hex):
        raise WebhookAuthError("Webhook signature verification failed.")


def handle_invoice_paid(
    conn: sqlite3.Connection,
    raw_body: bytes,
    signature_header: str,
) -> dict:
    """
    Process an invoice.paid webhook delivery.

    Returns a response dict suitable for the HTTP layer.
    """
    verify_signature(raw_body, signature_header)

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return {"status": 400, "body": {"error": f"Invalid JSON: {exc}"}}

    event_type = event.get("type")
    if event_type != "invoice.paid":
        # Acknowledge unknown event types without processing them.
        return {"status": 200, "body": {"received": True, "processed": False}}

    data       = event.get("data", {})
    tenant_id  = data.get("tenant_id")
    invoice_id = data.get("invoice_id")
    amount     = data.get("amount_cents")
    currency   = data.get("currency", "usd")
    idem_key   = event.get("id")  # provider's unique event ID

    if not all([tenant_id, invoice_id, amount is not None, idem_key]):
        return {"status": 400, "body": {"error": "Missing required fields."}}

    try:
        conn.execute(
            """
            INSERT INTO ledger
                (id, tenant_id, invoice_id, amount_cents, currency,
                 event_type, idempotency_key)
            VALUES (?, ?, ?, ?, ?, 'invoice.paid', ?)
            """,
            (str(uuid.uuid4()), tenant_id, invoice_id, amount, currency, idem_key),
        )
        conn.commit()
        logger.info("Ledger entry created for invoice %s tenant %s", invoice_id, tenant_id)
    except sqlite3.IntegrityError:
        # Duplicate delivery — idempotency_key already present.
        logger.info(
            "Duplicate invoice.paid delivery ignored (idem_key=%s)", idem_key
        )

    return {"status": 200, "body": {"received": True, "processed": True}}
