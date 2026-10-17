"""Tests for the internal ops-console operations."""

import uuid
import pytest

from reportkit.db import connect, apply_schema
from reportkit.handlers import ReportHandlers
from reportkit.ops import purge_tenant, set_role
from tests.conftest import _seed, _request


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


class TestPurgeTenant:
    def test_deletes_all_tenant_reports(self, conn):
        ctx = _seed(conn, role="editor")
        h   = ReportHandlers(conn)
        for i in range(3):
            h.create_report(_request(ctx["token"], body={"title": f"R{i}"}))

        count = purge_tenant(conn, actor_id="ops-bot", tenant_id=ctx["tenant_id"])
        assert count == 3

        remaining = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE tenant_id = ?",
            (ctx["tenant_id"],),
        ).fetchone()[0]
        assert remaining == 0

    def test_does_not_affect_other_tenants(self, conn):
        ctx_a = _seed(conn, role="editor")
        ctx_b = _seed(conn, role="editor")
        h     = ReportHandlers(conn)

        h.create_report(_request(ctx_a["token"], body={"title": "A"}))
        h.create_report(_request(ctx_b["token"], body={"title": "B"}))

        purge_tenant(conn, actor_id="ops", tenant_id=ctx_a["tenant_id"])

        remaining_b = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE tenant_id = ?",
            (ctx_b["tenant_id"],),
        ).fetchone()[0]
        assert remaining_b == 1

    def test_returns_zero_for_empty_tenant(self, conn):
        ctx   = _seed(conn, role="editor")
        count = purge_tenant(conn, actor_id="ops", tenant_id=ctx["tenant_id"])
        assert count == 0


class TestSetRole:
    def test_changes_role(self, conn):
        ctx = _seed(conn, role="viewer")
        set_role(conn, "ops", ctx["user_id"], ctx["tenant_id"], "admin")
        row = conn.execute(
            "SELECT role FROM roles WHERE user_id = ? AND tenant_id = ?",
            (ctx["user_id"], ctx["tenant_id"]),
        ).fetchone()
        assert row["role"] == "admin"

    def test_invalid_role_raises(self, conn):
        ctx = _seed(conn, role="viewer")
        with pytest.raises(ValueError, match="Unknown role"):
            set_role(conn, "ops", ctx["user_id"], ctx["tenant_id"], "superuser")

    def test_upsert_does_not_duplicate(self, conn):
        ctx = _seed(conn, role="viewer")
        set_role(conn, "ops", ctx["user_id"], ctx["tenant_id"], "editor")
        set_role(conn, "ops", ctx["user_id"], ctx["tenant_id"], "admin")
        count = conn.execute(
            "SELECT COUNT(*) FROM roles WHERE user_id = ?",
            (ctx["user_id"],),
        ).fetchone()[0]
        assert count == 1
