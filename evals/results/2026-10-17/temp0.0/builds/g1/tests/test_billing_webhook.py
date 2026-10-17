"""Billing webhook tests — HMAC auth, idempotency, replay protection."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid

import pytest

from reportkit.service import ReportService, _BILLING_SECRET_ENV


_SECRET = "test_billing_secret_abc123"


def _sign(secret: str, ts: int, body: bytes) -> str:
    signed = f"{ts}.".encode() + body
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def _webhook_request(
    payload: dict,
    *,
    secret: str = _SECRET,
    ts_offset: int = 0,
    bad_sig: bool = False,
    omit_sig: bool = False,
    omit_ts: bool = False,
) -> dict:
    body = json.dumps(payload).encode()
    ts = int(time.time()) + ts_offset
    sig = _sign(secret, ts, body)
    headers: dict = {}
    if not omit_sig:
        headers["X-Billing-Signature"] = "wrong_sig" if bad_sig else sig
    if not omit_ts:
        headers["X-Billing-Timestamp"] = str(ts)
    return {"headers": headers, "raw_body": body}


def _paid_payload(tenant_id: str | None = None) -> dict:
    return {
        "type": "invoice.paid",
        "id": str(uuid.uuid4()),
        "data": {
            "tenant_id": tenant_id or str(uuid.uuid4()),
            "amount": 9900,
            "currency": "USD",
        },
    }


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv(_BILLING_SECRET_ENV, _SECRET)


def test_valid_webhook_accepted(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    payload = _paid_payload(tid)
    resp = svc.billing_webhook(_webhook_request(payload))
    assert resp["status"] == 200
    assert resp["body"]["received"] is True

    row = conn.execute(
        "SELECT * FROM invoice_events WHERE event_id = ?", (payload["id"],)
    ).fetchone()
    assert row is not None
    assert row["amount"] == 9900
    assert row["currency"] == "USD"


def test_invalid_signature_rejected(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    resp = svc.billing_webhook(_webhook_request(_paid_payload(tid), bad_sig=True))
    assert resp["status"] == 401


def test_missing_signature_rejected(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    resp = svc.billing_webhook(_webhook_request(_paid_payload(tid), omit_sig=True))
    assert resp["status"] == 401


def test_missing_timestamp_rejected(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    resp = svc.billing_webhook(_webhook_request(_paid_payload(tid), omit_ts=True))
    assert resp["status"] == 401


def test_stale_timestamp_rejected(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    resp = svc.billing_webhook(_webhook_request(_paid_payload(tid), ts_offset=-400))
    assert resp["status"] == 401


def test_future_timestamp_rejected(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    resp = svc.billing_webhook(_webhook_request(_paid_payload(tid), ts_offset=400))
    assert resp["status"] == 401


def test_idempotent_duplicate_ignored(svc, conn):
    from tests.conftest import make_tenant
    tid = make_tenant(conn)
    payload = _paid_payload(tid)
    req = _webhook_request(payload)
    # First delivery
    r1 = svc.billing_webhook(req)
    assert r1["status"] == 200
    # Provider retries — same event_id
    # Must re-sign with a fresh timestamp
    r2 = svc.billing_webhook(_webhook_request(payload))
    assert r2["status"] == 200

    count = conn.execute(
        "SELECT COUNT(*) AS c FROM invoice_events WHERE event_id = ?", (payload["id"],)
    ).fetchone()["c"]
    assert count == 1


def test_unknown_event_type_acknowledged(svc, conn):
    payload = {"type": "invoice.voided", "id": str(uuid.uuid4()), "data": {}}
    resp = svc.billing_webhook(_webhook_request(payload))
    assert resp["status"] == 200


def test_invalid_tenant_uuid_rejected(svc, conn):
    payload = {
        "type": "invoice.paid",
        "id": str(uuid.uuid4()),
        "data": {"tenant_id": "not-a-uuid", "amount": 100, "currency": "USD"},
    }
    resp = svc.billing_webhook(_webhook_request(payload))
    assert resp["status"] == 400


def test_negative_amount_rejected(svc, conn):
    payload = {
        "type": "invoice.paid",
        "id": str(uuid.uuid4()),
        "data": {"tenant_id": str(uuid.uuid4()), "amount": -1, "currency": "USD"},
    }
    resp = svc.billing_webhook(_webhook_request(payload))
    assert resp["status"] == 400
