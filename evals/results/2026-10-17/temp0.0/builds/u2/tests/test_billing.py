"""Tests for the billing webhook handler."""

import hashlib
import hmac
import json
import os
import uuid
import pytest

from reportkit.db import connect, apply_schema
from reportkit.billing import handle_invoice_paid, verify_signature, WebhookAuthError


SECRET = "test-secret-key"


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", SECRET)


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    # Seed a tenant so FK constraints pass.
    c.execute("INSERT INTO tenants (id, name) VALUES ('t1', 'Test Tenant')")
    c.commit()
    return c


def _sign(body: bytes) -> str:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _event(tenant_id="t1", invoice_id=None, amount=1000, event_id=None):
    return {
        "id":   event_id or str(uuid.uuid4()),
        "type": "invoice.paid",
        "data": {
            "tenant_id":    tenant_id,
            "invoice_id":   invoice_id or str(uuid.uuid4()),
            "amount_cents": amount,
            "currency":     "usd",
        },
    }


class TestVerifySignature:
    def test_valid_signature_passes(self):
        body = b'{"hello": "world"}'
        verify_signature(body, _sign(body))  # no exception

    def test_invalid_signature_raises(self):
        body = b'{"hello": "world"}'
        with pytest.raises(WebhookAuthError):
            verify_signature(body, "sha256=deadbeef")

    def test_missing_prefix_raises(self):
        with pytest.raises(WebhookAuthError):
            verify_signature(b"body", "deadbeef")


class TestHandleInvoicePaid:
    def test_valid_event_creates_ledger_entry(self, conn):
        event = _event()
        body  = json.dumps(event).encode()
        resp  = handle_invoice_paid(conn, body, _sign(body))
        assert resp["status"] == 200
        row = conn.execute("SELECT * FROM ledger").fetchone()
        assert row is not None
        assert row["invoice_id"] == event["data"]["invoice_id"]

    def test_duplicate_delivery_is_idempotent(self, conn):
        event = _event(event_id="evt-001")
        body  = json.dumps(event).encode()
        sig   = _sign(body)
        handle_invoice_paid(conn, body, sig)
        handle_invoice_paid(conn, body, sig)  # second delivery
        count = conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
        assert count == 1

    def test_bad_signature_returns_error(self, conn):
        body = json.dumps(_event()).encode()
        with pytest.raises(WebhookAuthError):
            handle_invoice_paid(conn, body, "sha256=bad")

    def test_unknown_event_type_acknowledged(self, conn):
        event = {"id": "x", "type": "invoice.voided", "data": {}}
        body  = json.dumps(event).encode()
        resp  = handle_invoice_paid(conn, body, _sign(body))
        assert resp["status"] == 200
        assert resp["body"]["processed"] is False

    def test_missing_fields_returns_400(self, conn):
        event = {"id": "x", "type": "invoice.paid", "data": {}}
        body  = json.dumps(event).encode()
        resp  = handle_invoice_paid(conn, body, _sign(body))
        assert resp["status"] == 400


class TestMissingSecret:
    def test_raises_when_env_var_absent(self, conn, monkeypatch):
        monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
        body = json.dumps(_event()).encode()
        with pytest.raises(EnvironmentError):
            handle_invoice_paid(conn, body, "sha256=anything")
