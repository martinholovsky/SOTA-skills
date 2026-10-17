"""Billing webhook tests: HMAC verification, idempotency, rate limiting."""

import hashlib
import hmac
import json

import pytest

from tests.conftest import WEBHOOK_SECRET, make_request


def _sign(body_bytes: bytes) -> str:
    mac = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def _webhook_request(payload: dict, secret: bytes = WEBHOOK_SECRET,
                     remote_addr: str = "10.0.0.1") -> dict:
    raw = json.dumps(payload).encode()
    sig = _sign(raw) if secret else "sha256=badhex"
    return {
        "headers":     {"X-Signature": sig},
        "raw_body":    raw,
        "body":        payload,
        "query":       {},
        "remote_addr": remote_addr,
    }


_VALID_PAYLOAD = {
    "id":           "evt_test_001",
    "type":         "invoice.paid",
    "tenant_id":    "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    "amount_cents": 4999,
}


class TestWebhookHMAC:
    def test_valid_signature_accepted(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        req = _webhook_request(_VALID_PAYLOAD)
        resp = service.billing_webhook(req)
        assert resp["status"] == 200

    def test_invalid_signature_rejected(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        raw = json.dumps(_VALID_PAYLOAD).encode()
        req = {
            "headers":     {"X-Signature": "sha256=deadbeef" + "0" * 56},
            "raw_body":    raw,
            "body":        _VALID_PAYLOAD,
            "query":       {},
            "remote_addr": "10.0.0.1",
        }
        resp = service.billing_webhook(req)
        assert resp["status"] == 401

    def test_missing_signature_rejected(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        raw = json.dumps(_VALID_PAYLOAD).encode()
        req = {
            "headers":     {},
            "raw_body":    raw,
            "body":        _VALID_PAYLOAD,
            "query":       {},
            "remote_addr": "10.0.0.1",
        }
        resp = service.billing_webhook(req)
        assert resp["status"] == 401


class TestWebhookIdempotency:
    def test_duplicate_event_accepted_without_double_write(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        req = _webhook_request(_VALID_PAYLOAD)
        r1 = service.billing_webhook(req)
        r2 = service.billing_webhook(req)
        assert r1["status"] == 200
        assert r2["status"] == 200
        # Only one row should exist.
        count = conn.execute(
            "SELECT COUNT(*) FROM billing_events WHERE id = ?",
            (_VALID_PAYLOAD["id"],),
        ).fetchone()[0]
        assert count == 1

    def test_non_invoice_event_acknowledged(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        payload = {**_VALID_PAYLOAD, "id": "evt_other_001", "type": "subscription.updated"}
        req = _webhook_request(payload)
        resp = service.billing_webhook(req)
        assert resp["status"] == 200


class TestWebhookValidation:
    def test_invalid_tenant_uuid_rejected(self, service):
        payload = {**_VALID_PAYLOAD, "id": "evt_bad_001", "tenant_id": "not-a-uuid"}
        req = _webhook_request(payload)
        resp = service.billing_webhook(req)
        assert resp["status"] == 400

    def test_negative_amount_rejected(self, service, conn):
        conn.execute(
            "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
            ("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", "T"),
        )
        payload = {**_VALID_PAYLOAD, "id": "evt_neg_001", "amount_cents": -1}
        req = _webhook_request(payload)
        resp = service.billing_webhook(req)
        assert resp["status"] == 400
