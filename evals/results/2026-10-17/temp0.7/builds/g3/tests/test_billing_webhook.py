"""Tests for billing_webhook."""

import hashlib
import hmac
import json
import uuid
import pytest
from tests.conftest import make_tenant, auth_header


SECRET = b"testsecret"


def _sign(body: bytes) -> str:
    return hmac.new(SECRET, body, "sha256").hexdigest()


def _make_event(tenant_id, event_id=None, amount=1000):
    return {
        "type":         "invoice.paid",
        "id":           event_id or str(uuid.uuid4()),
        "tenant_id":    tenant_id,
        "invoice_id":   str(uuid.uuid4()),
        "amount_cents": amount,
    }


def test_valid_webhook_accepted(service, conn):
    tid = make_tenant(conn)
    payload = _make_event(tid)
    body = json.dumps(payload).encode()

    resp = service.billing_webhook({
        "headers":    {"X-Billing-Signature": _sign(body)},
        "raw_body":   body,
        "remote_addr": "10.0.0.1",
    })
    assert resp["status"] == 200
    assert resp["body"]["received"] is True


def test_missing_signature_rejected(service, conn):
    tid = make_tenant(conn)
    payload = _make_event(tid)
    body = json.dumps(payload).encode()

    resp = service.billing_webhook({
        "headers":   {},
        "raw_body":  body,
    })
    assert resp["status"] == 401


def test_wrong_signature_rejected(service, conn):
    tid = make_tenant(conn)
    payload = _make_event(tid)
    body = json.dumps(payload).encode()

    resp = service.billing_webhook({
        "headers":   {"X-Billing-Signature": "deadbeef" * 8},
        "raw_body":  body,
    })
    assert resp["status"] == 401


def test_duplicate_event_idempotent(service, conn):
    tid = make_tenant(conn)
    event_id = str(uuid.uuid4())
    payload = _make_event(tid, event_id=event_id)
    body = json.dumps(payload).encode()
    sig = _sign(body)

    r1 = service.billing_webhook({
        "headers":   {"X-Billing-Signature": sig},
        "raw_body":  body,
    })
    r2 = service.billing_webhook({
        "headers":   {"X-Billing-Signature": sig},
        "raw_body":  body,
    })
    assert r1["status"] == 200
    assert r2["status"] == 200
    assert r2["body"].get("duplicate") is True


def test_unknown_event_type_ignored(service, conn):
    payload = {"type": "invoice.voided", "id": str(uuid.uuid4())}
    body = json.dumps(payload).encode()

    resp = service.billing_webhook({
        "headers":   {"X-Billing-Signature": _sign(body)},
        "raw_body":  body,
    })
    assert resp["status"] == 200


def test_negative_amount_rejected(service, conn):
    tid = make_tenant(conn)
    payload = _make_event(tid, amount=-1)
    body = json.dumps(payload).encode()

    resp = service.billing_webhook({
        "headers":   {"X-Billing-Signature": _sign(body)},
        "raw_body":  body,
    })
    assert resp["status"] == 400


def test_tampered_body_rejected(service, conn):
    """Signature over original body must not verify against a modified body."""
    tid = make_tenant(conn)
    payload = _make_event(tid)
    body = json.dumps(payload).encode()
    sig = _sign(body)

    tampered = json.dumps({**payload, "amount_cents": 1}).encode()

    resp = service.billing_webhook({
        "headers":   {"X-Billing-Signature": sig},
        "raw_body":  tampered,
    })
    assert resp["status"] == 401
