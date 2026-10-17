"""Tests for the HTTP surface (ReportHandlers)."""

import uuid
import pytest

from reportkit.db import connect, apply_schema
from reportkit.handlers import ReportHandlers
from tests.conftest import _seed, _request


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------

class TestCreateReport:
    def test_editor_can_create(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.create_report(_request(ctx["token"], body={"title": "Q1 Report"}))
        assert resp["status"] == 201
        assert resp["body"]["title"] == "Q1 Report"
        assert resp["body"]["owner_id"] == ctx["user_id"]

    def test_viewer_cannot_create(self, viewer_ctx):
        conn, ctx, h = viewer_ctx
        resp = h.create_report(_request(ctx["token"], body={"title": "X"}))
        assert resp["status"] == 403

    def test_missing_title_returns_400(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.create_report(_request(ctx["token"], body={}))
        assert resp["status"] == 400

    def test_unauthenticated_returns_401(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.create_report({"headers": {}, "body": {"title": "X"}, "query": {}})
        assert resp["status"] == 401


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------

class TestGetReport:
    def _create(self, h, token, title="Test"):
        resp = h.create_report(_request(token, body={"title": title}))
        assert resp["status"] == 201
        return resp["body"]["id"]

    def test_owner_can_read(self, editor_ctx):
        conn, ctx, h = editor_ctx
        rid = self._create(h, ctx["token"])
        resp = h.get_report(_request(ctx["token"]), rid)
        assert resp["status"] == 200
        assert resp["body"]["id"] == rid

    def test_not_found_returns_404(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.get_report(_request(ctx["token"]), str(uuid.uuid4()))
        assert resp["status"] == 404

    def test_cross_tenant_isolation(self, conn):
        """A user from tenant B cannot read a report belonging to tenant A."""
        apply_schema(conn)
        h = ReportHandlers(conn)

        ctx_a = _seed(conn, role="editor")
        ctx_b = _seed(conn, role="editor")

        rid = h.create_report(
            _request(ctx_a["token"], body={"title": "Secret"})
        )["body"]["id"]

        resp = h.get_report(_request(ctx_b["token"]), rid)
        assert resp["status"] == 404


# ---------------------------------------------------------------------------
# list_reports
# ---------------------------------------------------------------------------

class TestListReports:
    def test_returns_own_reports_newest_first(self, editor_ctx):
        conn, ctx, h = editor_ctx
        h.create_report(_request(ctx["token"], body={"title": "First"}))
        h.create_report(_request(ctx["token"], body={"title": "Second"}))
        resp = h.list_reports(_request(ctx["token"]))
        assert resp["status"] == 200
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles[0] == "Second"
        assert titles[1] == "First"

    def test_viewer_can_list(self, viewer_ctx):
        conn, ctx, h = viewer_ctx
        resp = h.list_reports(_request(ctx["token"]))
        assert resp["status"] == 200

    def test_empty_list_for_new_user(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.list_reports(_request(ctx["token"]))
        assert resp["body"]["reports"] == []


# ---------------------------------------------------------------------------
# search_reports
# ---------------------------------------------------------------------------

class TestSearchReports:
    def _populate(self, h, token):
        for title in ("Alpha report", "Beta report", "Gamma note"):
            h.create_report(_request(token, body={"title": title}))

    def test_search_by_title_substring(self, editor_ctx):
        conn, ctx, h = editor_ctx
        self._populate(h, ctx["token"])
        resp = h.search_reports(_request(ctx["token"], query={"q": "report"}))
        assert resp["status"] == 200
        assert len(resp["body"]["reports"]) == 2

    def test_sort_by_title(self, editor_ctx):
        conn, ctx, h = editor_ctx
        self._populate(h, ctx["token"])
        resp = h.search_reports(
            _request(ctx["token"], query={"q": "", "sort": "title"})
        )
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles == sorted(titles)

    def test_invalid_sort_returns_400(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.search_reports(
            _request(ctx["token"], query={"sort": "'; DROP TABLE reports; --"})
        )
        assert resp["status"] == 400

    def test_sort_injection_rejected(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.search_reports(
            _request(ctx["token"], query={"sort": "owner_id"})
        )
        assert resp["status"] == 400

    def test_empty_query_returns_all(self, editor_ctx):
        conn, ctx, h = editor_ctx
        self._populate(h, ctx["token"])
        resp = h.search_reports(_request(ctx["token"], query={"q": ""}))
        assert len(resp["body"]["reports"]) == 3


# ---------------------------------------------------------------------------
# delete_report
# ---------------------------------------------------------------------------

class TestDeleteReport:
    def _create(self, h, token, title="To delete"):
        return h.create_report(_request(token, body={"title": title}))["body"]["id"]

    def test_admin_can_delete(self, admin_ctx):
        conn, ctx, h = admin_ctx
        rid = self._create(h, ctx["token"])
        resp = h.delete_report(_request(ctx["token"]), rid)
        assert resp["status"] == 200
        assert resp["body"]["deleted"] == rid

    def test_editor_cannot_delete(self, editor_ctx):
        conn, ctx, h = editor_ctx
        rid = self._create(h, ctx["token"])
        resp = h.delete_report(_request(ctx["token"]), rid)
        assert resp["status"] == 403

    def test_delete_nonexistent_returns_404(self, admin_ctx):
        conn, ctx, h = admin_ctx
        resp = h.delete_report(_request(ctx["token"]), str(uuid.uuid4()))
        assert resp["status"] == 404

    def test_deleted_report_not_retrievable(self, admin_ctx):
        conn, ctx, h = admin_ctx
        rid = self._create(h, ctx["token"])
        h.delete_report(_request(ctx["token"]), rid)
        resp = h.get_report(_request(ctx["token"]), rid)
        assert resp["status"] == 404


# ---------------------------------------------------------------------------
# upload_attachment
# ---------------------------------------------------------------------------

class TestUploadAttachment:
    def _create_report(self, h, token):
        return h.create_report(_request(token, body={"title": "R"}))["body"]["id"]

    def test_upload_succeeds(self, editor_ctx):
        conn, ctx, h = editor_ctx
        rid = self._create_report(h, ctx["token"])
        resp = h.upload_attachment(
            _request(
                ctx["token"],
                body={
                    "report_id": rid,
                    "filename":  "data.csv",
                    "data":      b"col1,col2\n1,2\n",
                },
            )
        )
        assert resp["status"] == 201
        assert resp["body"]["filename"] == "data.csv"

    def test_eicar_rejected(self, editor_ctx):
        conn, ctx, h = editor_ctx
        rid = self._create_report(h, ctx["token"])
        eicar = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
        resp = h.upload_attachment(
            _request(
                ctx["token"],
                body={"report_id": rid, "filename": "evil.txt", "data": eicar},
            )
        )
        assert resp["status"] == 422

    def test_oversized_rejected(self, editor_ctx):
        conn, ctx, h = editor_ctx
        rid = self._create_report(h, ctx["token"])
        big = b"x" * (25 * 1024 * 1024 + 1)
        resp = h.upload_attachment(
            _request(
                ctx["token"],
                body={"report_id": rid, "filename": "big.bin", "data": big},
            )
        )
        assert resp["status"] == 413

    def test_missing_report_id_returns_400(self, editor_ctx):
        conn, ctx, h = editor_ctx
        resp = h.upload_attachment(
            _request(ctx["token"], body={"filename": "f.txt", "data": b"hi"})
        )
        assert resp["status"] == 400

    def test_viewer_cannot_upload(self, viewer_ctx):
        conn, ctx, h = viewer_ctx
        resp = h.upload_attachment(
            _request(
                ctx["token"],
                body={"report_id": str(uuid.uuid4()), "filename": "f.txt", "data": b""},
            )
        )
        assert resp["status"] == 403
