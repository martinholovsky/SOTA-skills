"""Tests for the billing webhook handler."""

import hashlib
import hmac
import json
import os
import uuid

import pytest

from reportkit.billing import BillingError, handle_webhook
from tests.conftest import seed_tenant


SECRET = "test-secret-key"


def _sign(body_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def _make_request(payload: dict, secret: str = SECRET, bad_sig: bool = False):
    raw = json.dumps(payload).encode()
    sig = _sign(raw, secret) if not bad_sig else "deadbeef"
    return {
        "headers": {"X-Billing-Signature": sig},
        "raw_body": raw,
        "body": payload,
    }


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", SECRET)


class TestBillingWebhook:
    def test_valid_invoice_paid(self, conn):
        tid = seed_tenant(conn)
        payload = {"id": str(uuid.uuid4()), "type": "invoice.paid", "tenant_id": tid, "amount_cents": 5000}
        resp = handle_webhook(conn, _make_request(payload))
        assert resp["status"] == 200
        row = conn.execute("SELECT * FROM billing_events WHERE id = ?", (payload["id"],)).fetchone()
        assert row is not None
        assert row["amount_cents"] == 5000

    def test_invalid_signature_rejected(self, conn):
        tid = seed_tenant(conn)
        payload = {"id": str(uuid.uuid4()), "type": "invoice.paid", "tenant_id": tid, "amount_cents": 100}
        with pytest.raises(BillingError) as exc_info:
            handle_webhook(conn, _make_request(payload, bad_sig=True))
        assert exc_info.value.status == 401

    def test_idempotent_retry(self, conn):
        tid = seed_tenant(conn)
        event_id = str(uuid.uuid4())
        payload = {"id": event_id, "type": "invoice.paid", "tenant_id": tid, "amount_cents": 100}
        handle_webhook(conn, _make_request(payload))
        handle_webhook(conn, _make_request(payload))  # duplicate — should not raise
        count = conn.execute(
            "SELECT COUNT(*) FROM billing_events WHERE id = ?", (event_id,)
        ).fetchone()[0]
        assert count == 1

    def test_unknown_event_type_ignored(self, conn):
        tid = seed_tenant(conn)
        payload = {"id": str(uuid.uuid4()), "type": "invoice.voided", "tenant_id": tid}
        resp = handle_webhook(conn, _make_request(payload))
        assert resp["status"] == 200
        count = conn.execute("SELECT COUNT(*) FROM billing_events").fetchone()[0]
        assert count == 0

    def test_missing_secret_raises(self, conn, monkeypatch):
        monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
        payload = {"id": "x", "type": "invoice.paid", "tenant_id": "t"}
        with pytest.raises(BillingError) as exc_info:
            handle_webhook(conn, _make_request(payload))
        assert exc_info.value.status == 500

    def test_missing_signature_header(self, conn):
        payload = {"id": "x", "type": "invoice.paid", "tenant_id": "t"}
        raw = json.dumps(payload).encode()
        req = {"headers": {}, "raw_body": raw, "body": payload}
        with pytest.raises(BillingError) as exc_info:
            handle_webhook(conn, req)
        assert exc_info.value.status == 400
