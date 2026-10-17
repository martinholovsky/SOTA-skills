"""
Tests for the billing webhook handler.
"""

import hashlib
import hmac
import json
import time
import uuid

import pytest

from reportkit.errors import BadRequest, WebhookAuthFailed
from reportkit.webhook import handle_billing_webhook


def _uuid():
    return str(uuid.uuid4())


SECRET = b"test-webhook-secret-32-bytes-long!!"


def _sign(body: bytes, ts: int, secret: bytes = SECRET) -> str:
    payload = f"{ts}.".encode() + body
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _make_payload(tenant_id: str, event_id: str = None) -> bytes:
    return json.dumps({
        "id": event_id or _uuid(),
        "type": "invoice.paid",
        "data": {
            "tenant_id": tenant_id,
            "amount": 9900,
            "currency": "USD",
        },
    }).encode()


class TestWebhookAuth:
    def test_valid_signature_accepted(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        body = _make_payload(tenant_a)
        ts = int(time.time())
        sig = _sign(body, ts)
        result = handle_billing_webhook(db, body, sig, str(ts))
        assert result["status"] == "ok"

    def test_wrong_signature_rejected(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        body = _make_payload(tenant_a)
        ts = int(time.time())
        with pytest.raises(WebhookAuthFailed):
            handle_billing_webhook(db, body, "deadbeef" * 8, str(ts))

    def test_stale_timestamp_rejected(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr(
            "reportkit.webhook.Config.WEBHOOK_TIMESTAMP_TOLERANCE", 300
        )
        body = _make_payload(tenant_a)
        old_ts = int(time.time()) - 400
        sig = _sign(body, old_ts)
        with pytest.raises(WebhookAuthFailed):
            handle_billing_webhook(db, body, sig, str(old_ts))

    def test_future_timestamp_rejected(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr(
            "reportkit.webhook.Config.WEBHOOK_TIMESTAMP_TOLERANCE", 300
        )
        body = _make_payload(tenant_a)
        future_ts = int(time.time()) + 400
        sig = _sign(body, future_ts)
        with pytest.raises(WebhookAuthFailed):
            handle_billing_webhook(db, body, sig, str(future_ts))

    def test_missing_secret_raises(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", b"")
        body = _make_payload(tenant_a)
        ts = int(time.time())
        sig = _sign(body, ts, b"")
        with pytest.raises(WebhookAuthFailed):
            handle_billing_webhook(db, body, sig, str(ts))

    def test_invalid_timestamp_rejected(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        body = _make_payload(tenant_a)
        with pytest.raises(WebhookAuthFailed):
            handle_billing_webhook(db, body, "sig", "not-a-number")


class TestWebhookIdempotency:
    def test_duplicate_event_ignored(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        event_id = _uuid()
        body = _make_payload(tenant_a, event_id)
        ts = int(time.time())
        sig = _sign(body, ts)
        r1 = handle_billing_webhook(db, body, sig, str(ts))
        assert r1["status"] == "ok"
        # Second delivery with the same event_id.
        ts2 = int(time.time())
        sig2 = _sign(body, ts2)
        r2 = handle_billing_webhook(db, body, sig2, str(ts2))
        assert r2["status"] == "duplicate"

    def test_unknown_event_type_ignored(self, db, tenant_a, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        body = json.dumps({"id": _uuid(), "type": "invoice.voided"}).encode()
        ts = int(time.time())
        sig = _sign(body, ts)
        result = handle_billing_webhook(db, body, sig, str(ts))
        assert result["status"] == "ignored"


class TestWebhookValidation:
    def _call(self, db, body, monkeypatch):
        monkeypatch.setattr("reportkit.webhook.Config.BILLING_WEBHOOK_SECRET", SECRET)
        ts = int(time.time())
        sig = _sign(body, ts)
        return handle_billing_webhook(db, body, sig, str(ts))

    def test_invalid_json_raises(self, db, monkeypatch):
        with pytest.raises(BadRequest):
            self._call(db, b"not json", monkeypatch)

    def test_missing_tenant_id_raises(self, db, monkeypatch):
        body = json.dumps({
            "id": _uuid(),
            "type": "invoice.paid",
            "data": {"amount": 100, "currency": "USD"},
        }).encode()
        with pytest.raises(BadRequest):
            self._call(db, body, monkeypatch)

    def test_invalid_currency_raises(self, db, tenant_a, monkeypatch):
        body = json.dumps({
            "id": _uuid(),
            "type": "invoice.paid",
            "data": {"tenant_id": tenant_a, "amount": 100, "currency": "US"},
        }).encode()
        with pytest.raises(BadRequest):
            self._call(db, body, monkeypatch)

    def test_negative_amount_raises(self, db, tenant_a, monkeypatch):
        body = json.dumps({
            "id": _uuid(),
            "type": "invoice.paid",
            "data": {"tenant_id": tenant_a, "amount": -1, "currency": "USD"},
        }).encode()
        with pytest.raises(BadRequest):
            self._call(db, body, monkeypatch)
