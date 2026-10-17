"""
Billing webhook handler.

The billing provider POSTs `invoice.paid` events signed with an HMAC-SHA256
over the raw request body.  The shared secret is read from the environment.

Idempotency: the provider retries deliveries it considers failed.  We use the
provider's event id as a primary key so duplicate deliveries are silently
ignored.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone


class BillingError(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _verify_signature(raw_body: bytes, signature_header: str, secret: str) -> None:
    """
    Verify the HMAC-SHA256 signature supplied by the billing provider.

    The provider sends the signature as a hex digest in the
    ``X-Billing-Signature`` header.
    """
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header.lower()):
        raise BillingError("Invalid HMAC signature")


def handle_webhook(conn: sqlite3.Connection, request: dict) -> dict:
    """
    Process an inbound billing webhook.

    request keys
    ------------
    raw_body  : bytes  — the unmodified request body (for HMAC verification)
    headers   : dict   — HTTP headers; must contain X-Billing-Signature
    """
    secret = os.environ.get("BILLING_WEBHOOK_SECRET", "")
    if not secret:
        return {"status": 500, "error": "Billing webhook secret not configured"}

    raw_body: bytes = request.get("raw_body") or b""
    headers: dict   = request.get("headers") or {}
    signature: str  = headers.get("X-Billing-Signature") or headers.get("x-billing-signature") or ""

    if not signature:
        return {"status": 400, "error": "Missing X-Billing-Signature header"}

    try:
        _verify_signature(raw_body, signature, secret)
    except BillingError as exc:
        return {"status": 401, "error": str(exc)}

    # Parse payload
    try:
        payload: dict = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError) as exc:
        return {"status": 400, "error": f"Invalid JSON payload: {exc}"}

    event_id:   str = payload.get("id") or ""
    event_type: str = payload.get("type") or ""
    tenant_id:  str = payload.get("tenant_id") or ""
    amount_cents: int = int(payload.get("amount_cents") or 0)

    if not event_id:
        return {"status": 400, "error": "Payload missing 'id'"}
    if not tenant_id:
        return {"status": 400, "error": "Payload missing 'tenant_id'"}

    # Only handle invoice.paid for now
    if event_type != "invoice.paid":
        # Acknowledge unknown event types so the provider stops retrying
        return {"status": 200, "message": f"Event type '{event_type}' ignored"}

    # Idempotent insert — duplicate event ids are silently ignored
    try:
        conn.execute(
            """
            INSERT INTO billing_events (id, tenant_id, event_type, amount_cents, payload, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, event_type, amount_cents, raw_body.decode("utf-8", errors="replace"), _now_iso()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Duplicate delivery — already processed
        return {"status": 200, "message": "Duplicate event; already processed"}

    return {"status": 200, "message": "Payment recorded", "event_id": event_id}
