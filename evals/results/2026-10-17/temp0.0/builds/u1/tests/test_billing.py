"""Billing webhook tests."""

import hashlib
import hmac
import json
import os
import uuid
import pytest

from reportkit.billing import handle_webhook
from tests.conftest import seed_tenant


SECRET = "test-billing-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_payload(tenant_id, event_id=None, event_type="invoice.paid", amount=5000):
    return {
        "id": event_id or str(uuid.uuid4()),
        "type": event_type,
        "tenant_id": tenant_id,
        "amount_cents": amount,
    }


def _make_request(payload_dict, secret=SECRET):
    raw = json.dumps(payload_dict).encode()
    sig = _sign(raw, secret)
    return {"raw_body": raw, "headers": {"X-Billing-Signature": sig}}


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", SECRET)


def test_valid_invoice_paid(conn):
    tid = seed_tenant(conn)
    payload = _make_payload(tid)
    req = _make_request(payload)
    resp = handle_webhook(conn, req)
    assert resp["status"] == 200
    assert resp["event_id"] == payload["id"]


def test_duplicate_event_idempotent(conn):
    tid = seed_tenant(conn)
    event_id = str(uuid.uuid4())
    payload = _make_payload(tid, event_id=event_id)
    req = _make_request(payload)

    resp1 = handle_webhook(conn, req)
    assert resp1["status"] == 200

    resp2 = handle_webhook(conn, req)
    assert resp2["status"] == 200
    assert "already processed" in resp2["message"]


def test_invalid_signature_rejected(conn):
    tid = seed_tenant(conn)
    payload = _make_payload(tid)
    raw = json.dumps(payload).encode()
    req = {"raw_body": raw, "headers": {"X-Billing-Signature": "badsig"}}
    resp = handle_webhook(conn, req)
    assert resp["status"] == 401


def test_missing_signature_header(conn):
    tid = seed_tenant(conn)
    payload = _make_payload(tid)
    raw = json.dumps(payload).encode()
    req = {"raw_body": raw, "headers": {}}
    resp = handle_webhook(conn, req)
    assert resp["status"] == 400


def test_unknown_event_type_acknowledged(conn):
    tid = seed_tenant(conn)
    payload = _make_payload(tid, event_type="invoice.voided")
    req = _make_request(payload)
    resp = handle_webhook(conn, req)
    assert resp["status"] == 200
    assert "ignored" in resp["message"]


def test_missing_secret_env_var(conn, monkeypatch):
    monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
    tid = seed_tenant(conn)
    payload = _make_payload(tid)
    req = _make_request(payload)
    resp = handle_webhook(conn, req)
    assert resp["status"] == 500


def test_invalid_json_body(conn):
    sig = _sign(b"not json")
    req = {"raw_body": b"not json", "headers": {"X-Billing-Signature": sig}}
    resp = handle_webhook(conn, req)
    assert resp["status"] == 400
