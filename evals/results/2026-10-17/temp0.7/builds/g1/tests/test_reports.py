"""Report CRUD tests: create, get, list, search, delete."""

import pytest

from tests.conftest import make_request


class TestCreateReport:
    def test_editor_can_create(self, service, editor):
        req = make_request(editor["token"], body={"title": "Q1 Report", "body": "content"})
        resp = service.create_report(req)
        assert resp["status"] == 201
        assert resp["body"]["title"] == "Q1 Report"
        assert "id" in resp["body"]

    def test_viewer_cannot_create(self, service, viewer):
        req = make_request(viewer["token"], body={"title": "T", "body": ""})
        resp = service.create_report(req)
        assert resp["status"] == 403

    def test_missing_title_is_400(self, service, editor):
        req = make_request(editor["token"], body={"body": "content"})
        resp = service.create_report(req)
        assert resp["status"] == 400

    def test_empty_title_is_400(self, service, editor):
        req = make_request(editor["token"], body={"title": "", "body": ""})
        resp = service.create_report(req)
        assert resp["status"] == 400

    def test_nul_in_title_is_400(self, service, editor):
        req = make_request(editor["token"], body={"title": "bad\x00title", "body": ""})
        resp = service.create_report(req)
        assert resp["status"] == 400

    def test_unauthenticated_is_401(self, service):
        req = {"headers": {}, "body": {"title": "T", "body": ""}, "query": {}, "remote_addr": "1.2.3.4"}
        resp = service.create_report(req)
        assert resp["status"] == 401

    def test_title_too_long_is_400(self, service, editor):
        req = make_request(editor["token"], body={"title": "x" * 201, "body": ""})
        resp = service.create_report(req)
        assert resp["status"] == 400


class TestGetReport:
    def _create(self, service, editor):
        req = make_request(editor["token"], body={"title": "T", "body": "B"})
        resp = service.create_report(req)
        return resp["body"]["id"]

    def test_owner_can_get(self, service, editor):
        rid = self._create(service, editor)
        req = make_request(editor["token"])
        resp = service.get_report(req, rid)
        assert resp["status"] == 200
        assert resp["body"]["id"] == rid

    def test_other_tenant_cannot_get(self, service, editor, other_editor):
        rid = self._create(service, editor)
        req = make_request(other_editor["token"])
        resp = service.get_report(req, rid)
        # Must be 404, not 403 — don't leak existence
        assert resp["status"] == 404

    def test_viewer_same_tenant_can_read(self, service, editor, viewer):
        # viewer has report:read; the report is in the same tenant
        rid = self._create(service, editor)
        req = make_request(viewer["token"])
        resp = service.get_report(req, rid)
        # viewer can read reports in their tenant (report:read is the permission)
        assert resp["status"] == 200

    def test_invalid_uuid_is_400(self, service, editor):
        req = make_request(editor["token"])
        resp = service.get_report(req, "not-a-uuid")
        assert resp["status"] == 400

    def test_nonexistent_is_404(self, service, editor):
        req = make_request(editor["token"])
        resp = service.get_report(req, "00000000-0000-4000-8000-000000000000")
        assert resp["status"] == 404


class TestListReports:
    def test_returns_own_reports_only(self, service, editor, other_editor):
        # Create one report for editor
        r1 = make_request(editor["token"], body={"title": "Mine", "body": ""})
        service.create_report(r1)
        # Create one for other_editor
        r2 = make_request(other_editor["token"], body={"title": "Theirs", "body": ""})
        service.create_report(r2)

        req = make_request(editor["token"])
        resp = service.list_reports(req)
        assert resp["status"] == 200
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert "Mine" in titles
        assert "Theirs" not in titles

    def test_newest_first(self, service, editor):
        for title in ("A", "B", "C"):
            service.create_report(make_request(editor["token"], body={"title": title, "body": ""}))
        resp = service.list_reports(make_request(editor["token"]))
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles == ["C", "B", "A"]

    def test_empty_list_for_new_user(self, service, viewer):
        resp = service.list_reports(make_request(viewer["token"]))
        assert resp["status"] == 200
        assert resp["body"]["reports"] == []


class TestSearchReports:
    def _setup(self, service, editor):
        for title in ("Annual Budget", "Quarterly Review", "Budget Draft"):
            service.create_report(make_request(editor["token"], body={"title": title, "body": ""}))

    def test_search_by_title_substring(self, service, editor):
        self._setup(service, editor)
        req = make_request(editor["token"], query={"q": "Budget"})
        resp = service.search_reports(req)
        assert resp["status"] == 200
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert "Annual Budget" in titles
        assert "Budget Draft" in titles
        assert "Quarterly Review" not in titles

    def test_sort_by_title(self, service, editor):
        self._setup(service, editor)
        req = make_request(editor["token"], query={"q": "", "sort": "title"})
        resp = service.search_reports(req)
        assert resp["status"] == 200

    def test_invalid_sort_is_400(self, service, editor):
        req = make_request(editor["token"], query={"q": "x", "sort": "injected; DROP TABLE--"})
        resp = service.search_reports(req)
        assert resp["status"] == 400

    def test_sql_injection_in_query_is_safe(self, service, editor):
        # The search term is parameterized; this should return 0 results, not error.
        self._setup(service, editor)
        req = make_request(editor["token"], query={"q": "' OR '1'='1"})
        resp = service.search_reports(req)
        assert resp["status"] == 200
        assert resp["body"]["reports"] == []

    def test_like_metachar_in_query_does_not_match_all(self, service, editor):
        self._setup(service, editor)
        # A bare % would match everything if not escaped.
        req = make_request(editor["token"], query={"q": "%"})
        resp = service.search_reports(req)
        assert resp["status"] == 200
        # Should match nothing (% was escaped to \%, so no title contains literal %).
        assert resp["body"]["reports"] == []

    def test_cross_tenant_search_isolation(self, service, editor, other_editor):
        service.create_report(make_request(editor["token"], body={"title": "Secret", "body": ""}))
        req = make_request(other_editor["token"], query={"q": "Secret"})
        resp = service.search_reports(req)
        assert resp["status"] == 200
        assert resp["body"]["reports"] == []

    def test_empty_query_returns_all_own_reports(self, service, editor):
        self._setup(service, editor)
        req = make_request(editor["token"], query={"q": ""})
        resp = service.search_reports(req)
        assert resp["status"] == 200
        assert len(resp["body"]["reports"]) == 3


class TestDeleteReport:
    def _create(self, service, token, title="T"):
        req = make_request(token, body={"title": title, "body": ""})
        return service.create_report(req)["body"]["id"]

    def test_admin_can_delete(self, service, admin):
        rid = self._create(service, admin["token"])
        req = make_request(admin["token"])
        resp = service.delete_report(req, rid)
        assert resp["status"] == 200
        assert resp["body"]["deleted"] == rid

    def test_editor_cannot_delete(self, service, editor):
        rid = self._create(service, editor["token"])
        req = make_request(editor["token"])
        resp = service.delete_report(req, rid)
        assert resp["status"] == 403

    def test_viewer_cannot_delete(self, service, viewer, admin):
        rid = self._create(service, admin["token"])
        req = make_request(viewer["token"])
        resp = service.delete_report(req, rid)
        assert resp["status"] == 403

    def test_cross_tenant_delete_is_404(self, service, admin, other_editor):
        rid = self._create(service, other_editor["token"])
        req = make_request(admin["token"])
        resp = service.delete_report(req, rid)
        assert resp["status"] == 404

    def test_deleted_report_is_gone(self, service, admin):
        rid = self._create(service, admin["token"])
        service.delete_report(make_request(admin["token"]), rid)
        resp = service.get_report(make_request(admin["token"]), rid)
        assert resp["status"] == 404

    def test_invalid_uuid_is_400(self, service, admin):
        resp = service.delete_report(make_request(admin["token"]), "bad-id")
        assert resp["status"] == 400
