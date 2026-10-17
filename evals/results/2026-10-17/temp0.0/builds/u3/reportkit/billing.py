"""
Billing webhook handler.

The billing provider POSTs JSON bodies signed with HMAC-SHA256.
Signature header: ``X-Billing-Signature: sha256=<hex>``

Idempotency: the ``invoice_id`` is stored with a UNIQUE constraint;
duplicate deliveries are silently accepted (HTTP 200) without
double-counting.
"""

import hashlib
import hmac
import json
import logging
import os
import sqlite3

from .errors import AuthenticationError, ValidationError
from .ids import new_id

logger = logging.getLogger(__name__)

_SIGNATURE_HEADER = "X-Billing-Signature"


def _verify_signature(raw_body: bytes, header: str, secret: str) -> None:
    """Raise AuthenticationError if the HMAC signature is invalid."""
    if not header.startswith("sha256="):
        raise AuthenticationError("Missing or malformed billing signature.")
    provided = header[7:]
    expected = hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise AuthenticationError("Billing signature verification failed.")


def handle_webhook(
    conn: sqlite3.Connection,
    raw_body: bytes,
    headers: dict,
    *,
    secret: str | None = None,
) -> dict:
    """
    Process a billing webhook delivery.

    Parameters
    ----------
    conn      : open database connection
    raw_body  : the raw request body bytes (used for HMAC verification)
    headers   : HTTP headers dict (case-sensitive keys as sent by provider)
    secret    : HMAC secret; falls back to env var ``BILLING_WEBHOOK_SECRET``

    Returns a response dict ``{status, message}``.
    """
    if secret is None:
        secret = os.environ.get("BILLING_WEBHOOK_SECRET", "")
    if not secret:
        raise AuthenticationError("Billing webhook secret is not configured.")

    sig_header = headers.get(_SIGNATURE_HEADER, "")
    _verify_signature(raw_body, sig_header, secret)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON payload: {exc}") from exc

    event_type = payload.get("type")
    if event_type != "invoice.paid":
        # Unknown event types are acknowledged but not processed.
        return {"status": "ignored", "message": f"Unhandled event type: {event_type}"}

    data = payload.get("data", {})
    invoice_id   = data.get("invoice_id")
    tenant_id    = data.get("tenant_id")
    amount_cents = data.get("amount_cents")
    currency     = data.get("currency", "USD")

    if not all([invoice_id, tenant_id, isinstance(amount_cents, int)]):
        raise ValidationError(
            "invoice.paid payload missing required fields: "
            "invoice_id, tenant_id, amount_cents."
        )

    try:
        conn.execute(
            """
            INSERT INTO ledger (id, tenant_id, invoice_id, amount_cents, currency)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id(), tenant_id, invoice_id, amount_cents, currency),
        )
        conn.commit()
        logger.info("Recorded payment invoice=%s tenant=%s", invoice_id, tenant_id)
        return {"status": "ok", "message": "Payment recorded."}
    except sqlite3.IntegrityError:
        # Duplicate delivery — idempotent success.
        logger.info("Duplicate invoice delivery ignored: %s", invoice_id)
        return {"status": "ok", "message": "Already recorded."}
