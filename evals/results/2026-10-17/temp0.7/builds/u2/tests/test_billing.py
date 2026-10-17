"""Tests for the billing webhook handler."""

import hashlib
import hmac
import json
import os
import uuid

import pytest

from reportkit.billing import handle_webhook
from reportkit.errors import WebhookSignatureError, ValidationError
from reportkit.db import open_db, apply_schema
from reportkit.fixtures import make_tenant


SECRET = "test-billing-secret"


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
def conn():
    db = open_db(":memory:")
    apply_schema(db)
    return db


def _signed_request(payload: dict, secret: str = SECRET) -> dict:
    raw = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return {
        "body_bytes": raw,
        "headers":    {"X-Billing-Signature": sig},
    }


def test_invoice_paid_accepted(conn):
    tid = make_tenant(conn, "BillCo")
    event_id = str(uuid.uuid4())
    payload = {
        "id":           event_id,
        "type":         "invoice.paid",
        "tenant_id":    tid,
        "amount_cents": 4999,
    }
    resp = handle_webhook(conn, _signed_request(payload))
    assert resp["status"] == 200
    assert resp["body"]["processed"] is True


def test_invoice_paid_idempotent(conn):
    tid = make_tenant(conn, "BillCo2")
    event_id = str(uuid.uuid4())
    payload = {
        "id":           event_id,
        "type":         "invoice.paid",
        "tenant_id":    tid,
        "amount_cents": 100,
    }
    req = _signed_request(payload)
    handle_webhook(conn, req)
    resp2 = handle_webhook(conn, req)
    assert resp2["status"] == 200
    assert resp2["body"].get("duplicate") is True


def test_bad_signature_rejected(conn):
    payload = {"id": "x", "type": "invoice.paid", "tenant_id": "t", "amount_cents": 0}
    raw = json.dumps(payload).encode()
    req = {"body_bytes": raw, "headers": {"X-Billing-Signature": "deadbeef"}}
    with pytest.raises(WebhookSignatureError):
        handle_webhook(conn, req)


def test_missing_signature_rejected(conn):
    payload = {"id": "x", "type": "invoice.paid", "tenant_id": "t"}
    raw = json.dumps(payload).encode()
    req = {"body_bytes": raw, "headers": {}}
    with pytest.raises(WebhookSignatureError):
        handle_webhook(conn, req)


def test_unknown_event_type_acknowledged(conn):
    payload = {"id": str(uuid.uuid4()), "type": "invoice.voided", "tenant_id": "t"}
    resp = handle_webhook(conn, _signed_request(payload))
    assert resp["status"] == 200
    assert resp["body"]["processed"] is False


def test_missing_tenant_id_raises(conn):
    payload = {"id": str(uuid.uuid4()), "type": "invoice.paid", "amount_cents": 0}
    with pytest.raises(ValidationError):
        handle_webhook(conn, _signed_request(payload))
