"""Tests for ReportService HTTP surface methods."""

import pytest

from reportkit.errors import (
    AuthorisationError,
    NotFoundError,
    ValidationError,
)
from reportkit.fixtures import build_fixture_db
from reportkit.service import ReportService


def _req(token: str, body: dict | None = None, query: dict | None = None) -> dict:
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body":    body or {},
        "query":   query or {},
    }


class TestCreateReport:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)

    def test_editor_can_create(self):
        tok = self.ctx["tokens"]["editor"]
        result = self.svc.create_report(_req(tok, {"title": "Q1 Report"}))
        assert result["title"] == "Q1 Report"
        assert "id" in result

    def test_admin_can_create(self):
        tok = self.ctx["tokens"]["admin"]
        result = self.svc.create_report(_req(tok, {"title": "Admin Report"}))
        assert result["owner_id"] == self.ctx["users"]["admin"]

    def test_viewer_cannot_create(self):
        tok = self.ctx["tokens"]["viewer"]
        with pytest.raises(AuthorisationError):
            self.svc.create_report(_req(tok, {"title": "Sneaky"}))

    def test_missing_title_raises(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(ValidationError, match="title"):
            self.svc.create_report(_req(tok, {}))

    def test_blank_title_raises(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(ValidationError):
            self.svc.create_report(_req(tok, {"title": "   "}))

    def test_report_stored_in_db(self):
        tok = self.ctx["tokens"]["editor"]
        result = self.svc.create_report(_req(tok, {"title": "Stored"}))
        row = self.conn.execute(
            "SELECT * FROM reports WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row is not None
        assert row["title"] == "Stored"


class TestGetReport:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)
        tok = self.ctx["tokens"]["editor"]
        self.report = self.svc.create_report(_req(tok, {"title": "Fetchable"}))

    def test_viewer_can_get(self):
        tok = self.ctx["tokens"]["viewer"]
        result = self.svc.get_report(_req(tok), self.report["id"])
        assert result["id"] == self.report["id"]

    def test_unknown_report_raises(self):
        tok = self.ctx["tokens"]["viewer"]
        with pytest.raises(NotFoundError):
            self.svc.get_report(_req(tok), "00000000-0000-0000-0000-000000000000")

    def test_cross_tenant_isolation(self):
        """A report from another tenant must not be visible."""
        from reportkit.db import apply_schema, open_db
        from reportkit.ids import new_id
        from datetime import datetime, timedelta, timezone

        other_conn = open_db(":memory:")
        apply_schema(other_conn)
        tid2 = new_id()
        uid2 = new_id()
        tok2 = "other-tenant-token"
        other_conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tid2, "Other"))
        other_conn.execute(
            "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
            (uid2, tid2, "other_viewer", "viewer"),
        )
        exp = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%fZ"
        )
        other_conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (tok2, uid2, exp),
        )
        other_conn.commit()

        other_svc = ReportService(other_conn)
        with pytest.raises(NotFoundError):
            other_svc.get_report(_req(tok2), self.report["id"])


class TestListReports:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)

    def _create(self, title: str) -> dict:
        tok = self.ctx["tokens"]["editor"]
        return self.svc.create_report(_req(tok, {"title": title}))

    def test_returns_own_reports(self):
        self._create("Alpha")
        self._create("Beta")
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.list_reports(_req(tok))
        assert len(results) == 2

    def test_newest_first(self):
        self._create("First")
        self._create("Second")
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.list_reports(_req(tok))
        assert results[0]["title"] == "Second"

    def test_viewer_sees_only_own_reports(self):
        # Viewer has no reports; editor has some.
        self._create("Editor's report")
        tok = self.ctx["tokens"]["viewer"]
        results = self.svc.list_reports(_req(tok))
        assert results == []

    def test_empty_list_for_new_user(self):
        tok = self.ctx["tokens"]["admin"]
        results = self.svc.list_reports(_req(tok))
        assert results == []


class TestSearchReports:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)
        tok = self.ctx["tokens"]["editor"]
        for title in ("Annual Report 2023", "Quarterly Update", "Annual Summary"):
            self.svc.create_report(_req(tok, {"title": title}))

    def test_search_by_substring(self):
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.search_reports(_req(tok, query={"q": "Annual"}))
        assert len(results) == 2

    def test_empty_query_returns_all(self):
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.search_reports(_req(tok, query={"q": ""}))
        assert len(results) == 3

    def test_sort_by_title(self):
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.search_reports(_req(tok, query={"q": "", "sort": "title"}))
        titles = [r["title"] for r in results]
        assert titles == sorted(titles, reverse=True)

    def test_invalid_sort_raises(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(ValidationError, match="sort"):
            self.svc.search_reports(_req(tok, query={"sort": "owner_id; DROP TABLE reports--"}))

    def test_no_results(self):
        tok = self.ctx["tokens"]["editor"]
        results = self.svc.search_reports(_req(tok, query={"q": "zzznomatch"}))
        assert results == []


class TestDeleteReport:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)
        tok = self.ctx["tokens"]["editor"]
        self.report = self.svc.create_report(_req(tok, {"title": "To Delete"}))

    def test_admin_can_delete(self):
        tok = self.ctx["tokens"]["admin"]
        result = self.svc.delete_report(_req(tok), self.report["id"])
        assert result["deleted"] is True

    def test_editor_cannot_delete(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(AuthorisationError):
            self.svc.delete_report(_req(tok), self.report["id"])

    def test_viewer_cannot_delete(self):
        tok = self.ctx["tokens"]["viewer"]
        with pytest.raises(AuthorisationError):
            self.svc.delete_report(_req(tok), self.report["id"])

    def test_delete_nonexistent_raises(self):
        tok = self.ctx["tokens"]["admin"]
        with pytest.raises(NotFoundError):
            self.svc.delete_report(_req(tok), "00000000-0000-0000-0000-000000000000")

    def test_report_removed_from_db(self):
        tok = self.ctx["tokens"]["admin"]
        self.svc.delete_report(_req(tok), self.report["id"])
        row = self.conn.execute(
            "SELECT id FROM reports WHERE id = ?", (self.report["id"],)
        ).fetchone()
        assert row is None


class TestUploadAttachment:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)
        tok = self.ctx["tokens"]["editor"]
        self.report = self.svc.create_report(_req(tok, {"title": "With Attachment"}))

    def test_editor_can_upload(self):
        tok = self.ctx["tokens"]["editor"]
        result = self.svc.upload_attachment(_req(tok, {
            "report_id": self.report["id"],
            "filename":  "notes.txt",
            "data":      b"hello world",
        }))
        assert result["filename"] == "notes.txt"
        assert result["size_bytes"] == 11

    def test_viewer_cannot_upload(self):
        tok = self.ctx["tokens"]["viewer"]
        from reportkit.errors import AuthorisationError
        with pytest.raises(AuthorisationError):
            self.svc.upload_attachment(_req(tok, {
                "report_id": self.report["id"],
                "filename":  "x.txt",
                "data":      b"x",
            }))

    def test_missing_report_id_raises(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(ValidationError, match="report_id"):
            self.svc.upload_attachment(_req(tok, {"filename": "f.txt", "data": b"x"}))

    def test_missing_filename_raises(self):
        tok = self.ctx["tokens"]["editor"]
        with pytest.raises(ValidationError, match="filename"):
            self.svc.upload_attachment(_req(tok, {
                "report_id": self.report["id"],
                "data": b"x",
            }))

    def test_eicar_rejected(self):
        from reportkit.errors import ContentPolicyError
        tok = self.ctx["tokens"]["editor"]
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        with pytest.raises(ContentPolicyError):
            self.svc.upload_attachment(_req(tok, {
                "report_id": self.report["id"],
                "filename":  "eicar.com",
                "data":      eicar,
            }))

    def test_oversized_attachment_rejected(self):
        from reportkit.errors import ContentPolicyError
        tok = self.ctx["tokens"]["editor"]
        big = b"A" * (25 * 1024 * 1024 + 1)
        with pytest.raises(ContentPolicyError, match="size"):
            self.svc.upload_attachment(_req(tok, {
                "report_id": self.report["id"],
                "filename":  "big.bin",
                "data":      big,
            }))

    def test_attachment_stored_in_db(self):
        tok = self.ctx["tokens"]["editor"]
        result = self.svc.upload_attachment(_req(tok, {
            "report_id": self.report["id"],
            "filename":  "stored.txt",
            "data":      b"content",
        }))
        row = self.conn.execute(
            "SELECT * FROM attachments WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row is not None
        assert row["filename"] == "stored.txt"
