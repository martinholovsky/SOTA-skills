"""Inbound webhook intake from the billing provider."""
import hashlib
import hmac
import json

from reportkit import config


class BadSignature(Exception):
    pass


def verify(body, provided_sig):
    """Constant-time comparison of the HMAC over the raw body."""
    expected = hmac.new(config.WEBHOOK_KEY.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided_sig):
        raise BadSignature("signature mismatch")
    return True


def handle(body, headers, ledger):
    """Apply a billing event to the ledger."""
    verify(body, headers.get("X-Signature", ""))   # raises BadSignature -> 401

    try:
        event = json.loads(body)
    except ValueError:
        return {"applied": False, "status": 400, "reason": "invalid payload"}
    if event.get("type") == "invoice.paid":
        ledger.mark_paid(event["invoice_id"], event["amount_cents"])
        return {"applied": True}
    return {"applied": False}
