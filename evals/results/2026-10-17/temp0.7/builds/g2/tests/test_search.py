"""Search and sort tests — including injection probes."""

import pytest

from tests.conftest import _make_user, _req
from reportkit.service import ReportService


def _seed(svc, raw, titles):
    for t in titles:
        svc.create_report(_req(raw, body={"title": t, "body": ""}))


def test_search_finds_matching_title(db, svc, editor):
    _, _, raw = editor
    _seed(svc, raw, ["Alpha Report", "Beta Report", "Gamma"])
    resp = svc.search_reports(_req(raw, query={"q": "Report", "sort": "title"}))
    assert resp["status"] == 200
    titles = {r["title"] for r in resp["body"]["reports"]}
    assert "Alpha Report" in titles
    assert "Beta Report" in titles
    assert "Gamma" not in titles


def test_search_sort_created_at(db, svc, editor):
    _, _, raw = editor
    _seed(svc, raw, ["Z Report", "A Report"])
    resp = svc.search_reports(_req(raw, query={"q": "Report", "sort": "created_at"}))
    assert resp["status"] == 200


def test_search_sort_title(db, svc, editor):
    _, _, raw = editor
    _seed(svc, raw, ["Zebra", "Apple"])
    resp = svc.search_reports(_req(raw, query={"q": "e", "sort": "title"}))
    assert resp["status"] == 200


def test_search_invalid_sort_rejected(db, svc, editor):
    _, _, raw = editor
    resp = svc.search_reports(_req(raw, query={"q": "x", "sort": "id; DROP TABLE reports--"}))
    assert resp["status"] == 400


def test_search_sql_injection_in_query(db, svc, editor):
    """A LIKE-injection attempt must not widen the result set."""
    _, _, raw = editor
    _seed(svc, raw, ["Safe", "Other"])
    # '%' in the search term would match everything without escaping
    resp = svc.search_reports(_req(raw, query={"q": "%", "sort": "created_at"}))
    # Should return 0 results because '%' is escaped to '\%'
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_search_underscore_injection(db, svc, editor):
    """'_' wildcard must be escaped."""
    _, _, raw = editor
    _seed(svc, raw, ["A1", "A2", "AB"])
    resp = svc.search_reports(_req(raw, query={"q": "A_", "sort": "created_at"}))
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_search_no_cross_tenant(db, svc):
    """Search must not leak results from another tenant."""
    import uuid
    tid = str(uuid.uuid4())
    _, _, raw_a = _make_user(db, role="editor", tenant_id=tid)
    _, _, raw_b = _make_user(db, role="editor")  # different tenant

    svc.create_report(_req(raw_a, body={"title": "Secret Alpha", "body": ""}))

    resp = svc.search_reports(_req(raw_b, query={"q": "Secret", "sort": "created_at"}))
    assert resp["status"] == 200
    assert resp["body"]["reports"] == []


def test_search_query_too_long(db, svc, editor):
    _, _, raw = editor
    resp = svc.search_reports(_req(raw, query={"q": "x" * 200, "sort": "created_at"}))
    assert resp["status"] == 400


def test_search_nul_byte_rejected(db, svc, editor):
    _, _, raw = editor
    resp = svc.search_reports(_req(raw, query={"q": "abc\x00def", "sort": "created_at"}))
    assert resp["status"] == 400
