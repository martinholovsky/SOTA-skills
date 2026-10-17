"""Tests for ReportService HTTP methods."""

import uuid
import pytest

from tests.conftest import (
    make_request,
    seed_session,
    seed_tenant,
    seed_user,
)


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------

class TestCreateReport:
    def test_creates_report(self, service, editor):
        req = make_request(editor["token"], body={"title": "Q1 Report", "body": "content"})
        resp = service.create_report(req)
        assert resp["status"] == 201
        assert resp["body"]["title"] == "Q1 Report"
        assert resp["body"]["id"]

    def test_requires_title(self, service, editor):
        req = make_request(editor["token"], body={"body": "no title"})
        resp = service.create_report(req)
        assert resp["status"] == 400

    def test_viewer_cannot_create(self, service, viewer):
        req = make_request(viewer["token"], body={"title": "Denied"})
        resp = service.create_report(req)
        assert resp["status"] == 403

    def test_unauthenticated_rejected(self, service):
        req = make_request("bad-token", body={"title": "X"})
        resp = service.create_report(req)
        assert resp["status"] == 401

    def test_dispatches_event(self, conn, tenant):
        from reportkit.service import ReportService
        from reportkit.events import EventRegistry

        events = []
        reg = EventRegistry()
        reg.register("report.created", lambda p: events.append(p))
        svc = ReportService(conn, registry=reg)

        uid = seed_user(conn, tenant_id=tenant, role="editor")
        tok = seed_session(conn, user_id=uid)
        svc.create_report(make_request(tok, body={"title": "Evt"}))
        assert len(events) == 1
        assert "report_id" in events[0]


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------

class TestGetReport:
    def _create(self, service, editor):
        req = make_request(editor["token"], body={"title": "My Report"})
        return service.create_report(req)["body"]["id"]

    def test_get_own_report(self, service, editor):
        rid = self._create(service, editor)
        resp = service.get_report(make_request(editor["token"]), rid)
        assert resp["status"] == 200
        assert resp["body"]["id"] == rid

    def test_not_found(self, service, editor):
        resp = service.get_report(make_request(editor["token"]), str(uuid.uuid4()))
        assert resp["status"] == 404

    def test_cross_tenant_isolation(self, service, conn):
        """A user from tenant B cannot read a report belonging to tenant A."""
        tid_a = seed_tenant(conn)
        uid_a = seed_user(conn, tenant_id=tid_a, role="editor")
        tok_a = seed_session(conn, user_id=uid_a)

        tid_b = seed_tenant(conn)
        uid_b = seed_user(conn, tenant_id=tid_b, role="editor")
        tok_b = seed_session(conn, user_id=uid_b)

        rid = service.create_report(make_request(tok_a, body={"title": "Secret"}))["body"]["id"]
        resp = service.get_report(make_request(tok_b), rid)
        assert resp["status"] == 404

    def test_viewer_can_read(self, service, conn, tenant):
        uid_e = seed_user(conn, tenant_id=tenant, role="editor")
        tok_e = seed_session(conn, user_id=uid_e)
        rid = service.create_report(make_request(tok_e, body={"title": "Vis"}))["body"]["id"]

        uid_v = seed_user(conn, tenant_id=tenant, role="viewer")
        tok_v = seed_session(conn, user_id=uid_v)
        resp = service.get_report(make_request(tok_v), rid)
        assert resp["status"] == 200


# ---------------------------------------------------------------------------
# list_reports
# ---------------------------------------------------------------------------

class TestListReports:
    def test_returns_own_reports_newest_first(self, service, editor):
        tok = editor["token"]
        service.create_report(make_request(tok, body={"title": "First"}))
        service.create_report(make_request(tok, body={"title": "Second"}))
        resp = service.list_reports(make_request(tok))
        assert resp["status"] == 200
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles[0] == "Second"
        assert titles[1] == "First"

    def test_does_not_return_other_users_reports(self, service, conn, tenant):
        uid1 = seed_user(conn, tenant_id=tenant, role="editor")
        tok1 = seed_session(conn, user_id=uid1)
        uid2 = seed_user(conn, tenant_id=tenant, role="editor")
        tok2 = seed_session(conn, user_id=uid2)

        service.create_report(make_request(tok1, body={"title": "User1 Report"}))
        resp = service.list_reports(make_request(tok2))
        assert resp["body"]["reports"] == []

    def test_empty_list(self, service, editor):
        resp = service.list_reports(make_request(editor["token"]))
        assert resp["body"]["reports"] == []


# ---------------------------------------------------------------------------
# search_reports
# ---------------------------------------------------------------------------

class TestSearchReports:
    def _setup(self, service, tok):
        service.create_report(make_request(tok, body={"title": "Annual Budget 2024"}))
        service.create_report(make_request(tok, body={"title": "Q1 Sales Report"}))
        service.create_report(make_request(tok, body={"title": "Q2 Sales Report"}))

    def test_search_by_title(self, service, editor):
        self._setup(service, editor["token"])
        resp = service.search_reports(
            make_request(editor["token"], query={"q": "Sales"})
        )
        assert resp["status"] == 200
        assert len(resp["body"]["reports"]) == 2

    def test_search_no_results(self, service, editor):
        self._setup(service, editor["token"])
        resp = service.search_reports(
            make_request(editor["token"], query={"q": "Nonexistent"})
        )
        assert resp["body"]["reports"] == []

    def test_sort_by_title(self, service, editor):
        self._setup(service, editor["token"])
        resp = service.search_reports(
            make_request(editor["token"], query={"q": "Sales", "sort": "title"})
        )
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles == sorted(titles)

    def test_invalid_sort_falls_back_to_default(self, service, editor):
        self._setup(service, editor["token"])
        resp = service.search_reports(
            make_request(editor["token"], query={"q": "Sales", "sort": "id; DROP TABLE reports--"})
        )
        assert resp["status"] == 200  # no crash, no injection

    def test_missing_q_returns_400(self, service, editor):
        resp = service.search_reports(make_request(editor["token"], query={}))
        assert resp["status"] == 400

    def test_special_chars_in_query(self, service, editor):
        tok = editor["token"]
        service.create_report(make_request(tok, body={"title": "100% Complete"}))
        resp = service.search_reports(make_request(tok, query={"q": "100%"}))
        assert len(resp["body"]["reports"]) == 1

    def test_cross_user_isolation(self, service, conn, tenant):
        uid1 = seed_user(conn, tenant_id=tenant, role="editor")
        tok1 = seed_session(conn, user_id=uid1)
        uid2 = seed_user(conn, tenant_id=tenant, role="editor")
        tok2 = seed_session(conn, user_id=uid2)

        service.create_report(make_request(tok1, body={"title": "Private Report"}))
        resp = service.search_reports(make_request(tok2, query={"q": "Private"}))
        assert resp["body"]["reports"] == []


# ---------------------------------------------------------------------------
# delete_report
# ---------------------------------------------------------------------------

class TestDeleteReport:
    def test_admin_can_delete(self, service, admin, editor):
        rid = service.create_report(
            make_request(editor["token"], body={"title": "To Delete"})
        )["body"]["id"]
        resp = service.delete_report(make_request(admin["token"]), rid)
        assert resp["status"] == 200
        assert resp["body"]["deleted"] is True

    def test_editor_cannot_delete(self, service, editor):
        rid = service.create_report(
            make_request(editor["token"], body={"title": "No Delete"})
        )["body"]["id"]
        resp = service.delete_report(make_request(editor["token"]), rid)
        assert resp["status"] == 403

    def test_delete_nonexistent(self, service, admin):
        resp = service.delete_report(make_request(admin["token"]), str(uuid.uuid4()))
        assert resp["status"] == 404

    def test_delete_cross_tenant_blocked(self, service, conn):
        tid_a = seed_tenant(conn)
        uid_a = seed_user(conn, tenant_id=tid_a, role="editor")
        tok_a = seed_session(conn, user_id=uid_a)
        rid = service.create_report(make_request(tok_a, body={"title": "A's Report"}))["body"]["id"]

        tid_b = seed_tenant(conn)
        uid_b = seed_user(conn, tenant_id=tid_b, role="admin")
        tok_b = seed_session(conn, user_id=uid_b)
        resp = service.delete_report(make_request(tok_b), rid)
        assert resp["status"] == 404

    def test_dispatches_deleted_event(self, conn, tenant):
        from reportkit.service import ReportService
        from reportkit.events import EventRegistry

        events = []
        reg = EventRegistry()
        reg.register("report.deleted", lambda p: events.append(p))
        svc = ReportService(conn, registry=reg)

        uid = seed_user(conn, tenant_id=tenant, role="admin")
        tok = seed_session(conn, user_id=uid)
        rid = svc.create_report(make_request(tok, body={"title": "Del"}))["body"]["id"]
        svc.delete_report(make_request(tok), rid)
        assert len(events) == 1
        assert events[0]["report_id"] == rid


# ---------------------------------------------------------------------------
# upload_attachment
# ---------------------------------------------------------------------------

class TestUploadAttachment:
    def _report_id(self, service, editor):
        return service.create_report(
            make_request(editor["token"], body={"title": "Attach"})
        )["body"]["id"]

    def test_upload_clean_file(self, service, editor):
        rid = self._report_id(service, editor)
        req = make_request(
            editor["token"],
            body={
                "report_id": rid,
                "filename":  "hello.txt",
                "mime_type": "text/plain",
                "data":      b"Hello, world!",
            },
        )
        resp = service.upload_attachment(req)
        assert resp["status"] == 201
        assert resp["body"]["filename"] == "hello.txt"
        assert resp["body"]["size_bytes"] == 13

    def test_rejects_eicar(self, service, editor):
        rid = self._report_id(service, editor)
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        req = make_request(
            editor["token"],
            body={"report_id": rid, "filename": "eicar.com", "data": eicar},
        )
        resp = service.upload_attachment(req)
        assert resp["status"] == 422

    def test_rejects_oversized(self, service, editor):
        rid = self._report_id(service, editor)
        big = b"A" * (25 * 1024 * 1024 + 1)
        req = make_request(
            editor["token"],
            body={"report_id": rid, "filename": "big.bin", "data": big},
        )
        resp = service.upload_attachment(req)
        assert resp["status"] == 413

    def test_viewer_cannot_upload(self, service, viewer, editor):
        rid = self._report_id(service, editor)
        req = make_request(
            viewer["token"],
            body={"report_id": rid, "filename": "x.txt", "data": b"x"},
        )
        resp = service.upload_attachment(req)
        assert resp["status"] == 403

    def test_cross_tenant_report_blocked(self, service, conn):
        tid_a = seed_tenant(conn)
        uid_a = seed_user(conn, tenant_id=tid_a, role="editor")
        tok_a = seed_session(conn, user_id=uid_a)
        rid = service.create_report(make_request(tok_a, body={"title": "A"}))["body"]["id"]

        tid_b = seed_tenant(conn)
        uid_b = seed_user(conn, tenant_id=tid_b, role="editor")
        tok_b = seed_session(conn, user_id=uid_b)
        req = make_request(tok_b, body={"report_id": rid, "filename": "x.txt", "data": b"x"})
        resp = service.upload_attachment(req)
        assert resp["status"] == 404
