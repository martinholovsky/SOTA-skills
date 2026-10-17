"""Billing webhook tests — HMAC verification and idempotency."""

import hashlib
import hmac
import json
import os
import time
import pytest

from reportkit.service import ReportService
from tests.conftest import _make_user


SECRET = b"test-webhook-secret-32-bytes-long!"


def _sign(body: bytes, ts: int | None = None) -> dict:
    """Build a correctly signed request dict."""
    ts = ts or int(time.time())
    signed_payload = f"{ts}.".encode() + body
    sig = hmac.new(SECRET, signed_payload, hashlib.sha256).hexdigest()
    return {
        "headers": {
            "X-Webhook-Signature": f"t={ts},v1={sig}",
        },
        "raw_body": body,
        "body": {},
        "query": {},
    }


def _payload(**kwargs) -> bytes:
    base = {
        "type":      "invoice.paid",
        "id":        "evt_001",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "amount":    1000,
        "currency":  "USD",
    }
    base.update(kwargs)
    return json.dumps(base).encode()


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", SECRET.decode())


def test_valid_webhook_accepted(db, svc):
    body = _payload()
    resp = svc.handle_billing_webhook(_sign(body))
    assert resp["status"] == 200
    assert resp["body"]["processed"] is True


def test_invalid_signature_rejected(db, svc):
    body = _payload()
    req = _sign(body)
    # Tamper with the signature
    req["headers"]["X-Webhook-Signature"] = req["headers"]["X-Webhook-Signature"].replace(
        "v1=", "v1=00"
    )
    resp = svc.handle_billing_webhook(req)
    assert resp["status"] == 400


def test_replayed_webhook_rejected(db, svc):
    """A timestamp outside the 5-minute window is rejected."""
    body = _payload()
    old_ts = int(time.time()) - 400   # 6+ minutes ago
    req = _sign(body, ts=old_ts)
    resp = svc.handle_billing_webhook(req)
    assert resp["status"] == 400


def test_duplicate_event_idempotent(db, svc):
    body = _payload(id="evt_dup")
    req = _sign(body)
    r1 = svc.handle_billing_webhook(req)
    assert r1["status"] == 200
    # Second delivery of the same event
    req2 = _sign(body)   # fresh timestamp, same event_id
    r2 = svc.handle_billing_webhook(req2)
    assert r2["status"] == 200
    assert r2["body"].get("duplicate") is True


def test_unknown_event_type_ignored(db, svc):
    body = json.dumps({
        "type":      "invoice.voided",
        "id":        "evt_002",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "amount":    0,
        "currency":  "USD",
    }).encode()
    resp = svc.handle_billing_webhook(_sign(body))
    assert resp["status"] == 200
    assert resp["body"].get("ignored") is True


def test_missing_secret_env_returns_500(db, svc, monkeypatch):
    monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
    body = _payload()
    req = _sign(body)
    resp = svc.handle_billing_webhook(req)
    assert resp["status"] == 500


def test_negative_amount_rejected(db, svc):
    body = _payload(amount=-1)
    resp = svc.handle_billing_webhook(_sign(body))
    assert resp["status"] == 400


def test_body_tampered_after_signing(db, svc):
    """Modifying the body after signing must be detected."""
    original = _payload()
    req = _sign(original)
    # Replace body with a tampered version
    tampered = _payload(amount=99999)
    req["raw_body"] = tampered
    resp = svc.handle_billing_webhook(req)
    assert resp["status"] == 400
