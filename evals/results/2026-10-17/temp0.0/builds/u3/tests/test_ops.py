"""Tests for internal ops-console operations."""

import pytest

from reportkit.errors import NotFoundError, ValidationError
from reportkit.fixtures import build_fixture_db
from reportkit.ops import purge_tenant, set_role
from reportkit.service import ReportService


def _req(token, body=None):
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body": body or {},
        "query": {},
    }


class TestPurgeTenant:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()
        self.svc = ReportService(self.conn)

    def _create_report(self, role="editor"):
        tok = self.ctx["tokens"][role]
        return self.svc.create_report(_req(tok, {"title": "Report"}))

    def test_purge_removes_all_reports(self):
        self._create_report()
        self._create_report()
        count = purge_tenant(self.conn, "ops-actor", self.ctx["tenant_id"])
        assert count == 2
        remaining = self.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        assert remaining == 0

    def test_purge_unknown_tenant_raises(self):
        with pytest.raises(NotFoundError):
            purge_tenant(self.conn, "ops-actor", "00000000-0000-0000-0000-000000000000")

    def test_purge_empty_tenant_returns_zero(self):
        count = purge_tenant(self.conn, "ops-actor", self.ctx["tenant_id"])
        assert count == 0


class TestSetRole:
    def setup_method(self):
        self.conn, self.ctx = build_fixture_db()

    def test_set_valid_role(self):
        uid = self.ctx["users"]["viewer"]
        set_role(self.conn, "ops-actor", uid, "editor")
        row = self.conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
        assert row["role"] == "editor"

    def test_invalid_role_raises(self):
        uid = self.ctx["users"]["viewer"]
        with pytest.raises(ValidationError, match="role"):
            set_role(self.conn, "ops-actor", uid, "superuser")

    def test_unknown_user_raises(self):
        with pytest.raises(NotFoundError):
            set_role(self.conn, "ops-actor", "00000000-0000-0000-0000-000000000000", "admin")

    def test_role_change_reflected_in_permissions(self):
        """After set_role, the user's new permissions are active on next auth."""
        from reportkit.auth import resolve_caller
        uid = self.ctx["users"]["viewer"]
        tok = self.ctx["tokens"]["viewer"]

        caller_before = resolve_caller(self.conn, tok)
        assert "report:write" not in caller_before["permissions"]

        set_role(self.conn, "ops-actor", uid, "editor")

        caller_after = resolve_caller(self.conn, tok)
        assert "report:write" in caller_after["permissions"]
