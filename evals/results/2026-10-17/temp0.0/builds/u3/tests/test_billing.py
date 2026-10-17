"""Tests for the billing webhook handler."""

import hashlib
import hmac
import json

import pytest

from reportkit.billing import handle_webhook
from reportkit.errors import AuthenticationError, ValidationError
from reportkit.fixtures import build_fixture_db

SECRET = "test-secret-key"


def _sign(body: bytes, secret: str = SECRET) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _headers(body: bytes, secret: str = SECRET) -> dict:
    return {"X-Billing-Signature": _sign(body, secret)}


def _paid_event(tenant_id: str, invoice_id: str = "inv_001") -> bytes:
    return json.dumps({
        "type": "invoice.paid",
        "data": {
            "invoice_id":   invoice_id,
            "tenant_id":    tenant_id,
            "amount_cents": 4999,
            "currency":     "USD",
        },
    }).encode()


class TestBillingWebhook:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()

    def test_valid_payment_recorded(self):
        body = _paid_event(self.ctx["tenant_id"])
        result = handle_webhook(self.conn, body, _headers(body), secret=SECRET)
        assert result["status"] == "ok"
        row = self.conn.execute("SELECT * FROM ledger WHERE invoice_id = 'inv_001'").fetchone()
        assert row is not None
        assert row["amount_cents"] == 4999

    def test_duplicate_delivery_is_idempotent(self):
        body = _paid_event(self.ctx["tenant_id"])
        handle_webhook(self.conn, body, _headers(body), secret=SECRET)
        result = handle_webhook(self.conn, body, _headers(body), secret=SECRET)
        assert result["status"] == "ok"
        count = self.conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
        assert count == 1

    def test_bad_signature_raises(self):
        body = _paid_event(self.ctx["tenant_id"])
        bad_headers = {"X-Billing-Signature": "sha256=deadbeef"}
        with pytest.raises(AuthenticationError, match="signature"):
            handle_webhook(self.conn, body, bad_headers, secret=SECRET)

    def test_missing_signature_raises(self):
        body = _paid_event(self.ctx["tenant_id"])
        with pytest.raises(AuthenticationError):
            handle_webhook(self.conn, body, {}, secret=SECRET)

    def test_unknown_event_type_ignored(self):
        payload = json.dumps({"type": "invoice.voided", "data": {}}).encode()
        result = handle_webhook(self.conn, payload, _headers(payload), secret=SECRET)
        assert result["status"] == "ignored"

    def test_missing_fields_raises(self):
        payload = json.dumps({
            "type": "invoice.paid",
            "data": {"invoice_id": "x"},
        }).encode()
        with pytest.raises(ValidationError):
            handle_webhook(self.conn, payload, _headers(payload), secret=SECRET)

    def test_invalid_json_raises(self):
        body = b"not json {"
        with pytest.raises(ValidationError, match="JSON"):
            handle_webhook(self.conn, body, _headers(body), secret=SECRET)

    def test_tampered_body_raises(self):
        body = _paid_event(self.ctx["tenant_id"])
        headers = _headers(body)
        tampered = body + b" "
        with pytest.raises(AuthenticationError):
            handle_webhook(self.conn, tampered, headers, secret=SECRET)
