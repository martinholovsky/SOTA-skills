"""Authentication and session tests."""

import time
import uuid

import pytest

from tests.conftest import _make_user, _req
from reportkit.service import ReportService
from reportkit.crypto import hash_token, generate_token


def test_missing_token_returns_401(db, svc):
    resp = svc.list_reports({"headers": {}, "body": {}, "query": {}})
    assert resp["status"] == 401


def test_bad_token_returns_401(db, svc):
    resp = svc.list_reports(_req("notavalidtoken"))
    assert resp["status"] == 401


def test_expired_token_returns_401(db):
    tid, uid, raw = _make_user(db, role="viewer")
    # Overwrite session with an expired timestamp
    db.execute(
        "UPDATE sessions SET expires_at=? WHERE token_hash=?",
        (int(time.time()) - 1, hash_token(raw)),
    )
    db.commit()
    svc = ReportService(db)
    resp = svc.list_reports(_req(raw))
    assert resp["status"] == 401


def test_suspended_tenant_returns_403(db):
    tid, uid, raw = _make_user(db, role="editor")
    db.execute("UPDATE tenants SET suspended=1 WHERE id=?", (tid,))
    db.commit()
    svc = ReportService(db)
    resp = svc.create_report(_req(raw, body={"title": "T", "body": "B"}))
    assert resp["status"] == 403


def test_viewer_cannot_create(db, svc, viewer):
    _, _, raw = viewer
    resp = svc.create_report(_req(raw, body={"title": "T", "body": "B"}))
    assert resp["status"] == 403


def test_viewer_cannot_delete(db, svc, viewer):
    _, _, raw = viewer
    resp = svc.delete_report(_req(raw), str(uuid.uuid4()))
    assert resp["status"] == 403


def test_editor_can_create(db, svc, editor):
    _, _, raw = editor
    resp = svc.create_report(_req(raw, body={"title": "Hello", "body": "World"}))
    assert resp["status"] == 200
    assert "report_id" in resp["body"]


def test_admin_can_delete_own_report(db, svc, admin):
    _, _, raw = admin
    create = svc.create_report(_req(raw, body={"title": "Del me", "body": "x"}))
    rid = create["body"]["report_id"]
    resp = svc.delete_report(_req(raw), rid)
    assert resp["status"] == 200


def test_empty_bearer_returns_401(db, svc):
    resp = svc.list_reports({"headers": {"Authorization": "Bearer "}, "body": {}, "query": {}})
    assert resp["status"] == 401
