"""Tests for billing webhook handling."""
import hashlib
import hmac
import json
import uuid
import pytest

from reportkit.db import connect, apply_schema
from reportkit.billing import handle_webhook, BillingError
from reportkit.auth import AuthError
from reportkit import fixtures as F


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


SECRET = "test-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _payload(tenant_id: str, event_id: str | None = None) -> bytes:
    return json.dumps({
        "id":        event_id or str(uuid.uuid4()),
        "type":      "invoice.paid",
        "tenant_id": tenant_id,
        "data": {
            "invoice_id":   "inv_001",
            "amount_cents": 4999,
            "currency":     "usd",
        },
    }).encode()


def test_valid_webhook(conn):
    tid = F.make_tenant(conn)
    body = _payload(tid)
    result = handle_webhook(conn, body, _sign(body), SECRET)
    assert result["status"] == "recorded"


def test_duplicate_webhook_idempotent(conn):
    tid = F.make_tenant(conn)
    event_id = str(uuid.uuid4())
    body = _payload(tid, event_id)
    handle_webhook(conn, body, _sign(body), SECRET)
    result = handle_webhook(conn, body, _sign(body), SECRET)
    assert result["status"] == "duplicate"


def test_bad_signature(conn):
    tid = F.make_tenant(conn)
    body = _payload(tid)
    with pytest.raises(AuthError):
        handle_webhook(conn, body, "sha256=badhex", SECRET)


def test_missing_signature(conn):
    tid = F.make_tenant(conn)
    body = _payload(tid)
    with pytest.raises(AuthError):
        handle_webhook(conn, body, "", SECRET)


def test_ignored_event_type(conn):
    tid = F.make_tenant(conn)
    body = json.dumps({"id": "e1", "type": "invoice.voided", "tenant_id": tid}).encode()
    result = handle_webhook(conn, body, _sign(body), SECRET)
    assert result["status"] == "ignored"


def test_missing_secret_raises(conn):
    tid = F.make_tenant(conn)
    body = _payload(tid)
    with pytest.raises(BillingError, match="BILLING_WEBHOOK_SECRET"):
        handle_webhook(conn, body, _sign(body), secret="")


def test_malformed_json(conn):
    body = b"not json"
    with pytest.raises(BillingError):
        handle_webhook(conn, body, _sign(body), SECRET)
