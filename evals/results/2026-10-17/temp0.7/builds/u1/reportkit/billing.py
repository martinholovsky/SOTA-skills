"""
Billing webhook handler.

The billing provider posts ``invoice.paid`` events signed with an HMAC-SHA256
over the raw request body.  The shared secret is read from the environment.

Idempotency: the provider retries deliveries it considers failed.  We use the
provider-supplied event ``id`` as a unique key in ``billing_events`` to
deduplicate retries.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import uuid

logger = logging.getLogger(__name__)

_HEADER_SIGNATURE = "X-Billing-Signature"
_ENV_SECRET       = "BILLING_WEBHOOK_SECRET"


class BillingError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_signature(raw_body: bytes, provided_sig: str, secret: str) -> None:
    """
    Verify the HMAC-SHA256 signature sent by the billing provider.

    The provider computes ``HMAC-SHA256(secret, raw_body)`` and sends the hex
    digest in ``X-Billing-Signature``.
    """
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    # Use compare_digest to avoid timing attacks.
    if not hmac.compare_digest(expected, provided_sig):
        raise BillingError("Invalid webhook signature.", status=401)


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------

def handle_webhook(conn: sqlite3.Connection, request: dict) -> dict:
    """
    Process a billing webhook request.

    *request* keys:
    - ``headers``  – dict of HTTP headers (must include ``X-Billing-Signature``)
    - ``raw_body`` – ``bytes`` of the unmodified request body
    - ``body``     – parsed JSON dict (convenience; derived from ``raw_body``)

    Returns a response dict ``{"status": 200, "body": {"received": True}}``.
    """
    secret = os.environ.get(_ENV_SECRET, "")
    if not secret:
        logger.error("BILLING_WEBHOOK_SECRET is not set.")
        raise BillingError("Webhook secret not configured.", status=500)

    headers = request.get("headers") or {}
    provided_sig = headers.get(_HEADER_SIGNATURE, "")
    if not provided_sig:
        raise BillingError(f"Missing {_HEADER_SIGNATURE} header.", status=400)

    raw_body: bytes = request.get("raw_body", b"")
    _verify_signature(raw_body, provided_sig, secret)

    # Parse body (accept pre-parsed dict or raw bytes)
    body = request.get("body")
    if body is None:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise BillingError(f"Invalid JSON body: {exc}", status=400) from exc

    event_type = body.get("type", "")
    event_id   = body.get("id") or str(uuid.uuid4())
    tenant_id  = body.get("tenant_id", "")
    amount     = int(body.get("amount_cents", 0))

    if event_type != "invoice.paid":
        # Unknown event types are accepted but not stored — forward-compatible.
        logger.info("Ignoring billing event type '%s'.", event_type)
        return {"status": 200, "body": {"received": True}}

    if not tenant_id:
        raise BillingError("Missing tenant_id in payload.", status=400)

    # Idempotent insert — ignore duplicate event ids.
    try:
        conn.execute(
            """
            INSERT INTO billing_events (id, tenant_id, event_type, amount_cents, raw_payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, event_type, amount, raw_body.decode("utf-8", errors="replace")),
        )
        conn.commit()
        logger.info("Billing event %s recorded for tenant %s.", event_id, tenant_id)
    except sqlite3.IntegrityError:
        # Duplicate delivery — already processed.
        logger.info("Duplicate billing event %s ignored.", event_id)

    return {"status": 200, "body": {"received": True}}
