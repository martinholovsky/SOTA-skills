"""Tests for ops-console operations."""

import uuid
import pytest

from reportkit.ops import OpsError, purge_tenant, set_role
from tests.conftest import make_request, seed_session, seed_tenant, seed_user


class TestPurgeTenant:
    def test_deletes_all_reports(self, service, conn):
        tid = seed_tenant(conn)
        uid = seed_user(conn, tenant_id=tid, role="editor")
        tok = seed_session(conn, user_id=uid)
        service.create_report(make_request(tok, body={"title": "R1"}))
        service.create_report(make_request(tok, body={"title": "R2"}))

        deleted = purge_tenant(conn, actor_id="ops-bot", tenant_id=tid)
        assert deleted == 2

        count = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE tenant_id = ?", (tid,)
        ).fetchone()[0]
        assert count == 0

    def test_nonexistent_tenant_raises(self, conn):
        with pytest.raises(OpsError, match="not found"):
            purge_tenant(conn, actor_id="ops", tenant_id=str(uuid.uuid4()))

    def test_does_not_affect_other_tenants(self, service, conn):
        tid_a = seed_tenant(conn)
        uid_a = seed_user(conn, tenant_id=tid_a, role="editor")
        tok_a = seed_session(conn, user_id=uid_a)
        service.create_report(make_request(tok_a, body={"title": "A's Report"}))

        tid_b = seed_tenant(conn)
        uid_b = seed_user(conn, tenant_id=tid_b, role="editor")
        tok_b = seed_session(conn, user_id=uid_b)
        service.create_report(make_request(tok_b, body={"title": "B's Report"}))

        purge_tenant(conn, actor_id="ops", tenant_id=tid_a)

        count_b = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE tenant_id = ?", (tid_b,)
        ).fetchone()[0]
        assert count_b == 1


class TestSetRole:
    def test_changes_role(self, conn, tenant):
        uid = seed_user(conn, tenant_id=tenant, role="viewer")
        set_role(conn, actor_id="ops", user_id=uid, new_role="admin")
        row = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
        assert row["role"] == "admin"

    def test_invalid_role_raises(self, conn, tenant):
        uid = seed_user(conn, tenant_id=tenant, role="viewer")
        with pytest.raises(OpsError, match="Invalid role"):
            set_role(conn, actor_id="ops", user_id=uid, new_role="superuser")

    def test_nonexistent_user_raises(self, conn):
        with pytest.raises(OpsError, match="not found"):
            set_role(conn, actor_id="ops", user_id=str(uuid.uuid4()), new_role="editor")

    def test_role_change_reflected_in_next_request(self, service, conn, tenant):
        """After set_role, the next authenticated request sees the new permissions."""
        uid = seed_user(conn, tenant_id=tenant, role="viewer")
        tok = seed_session(conn, user_id=uid)

        # Viewer cannot create
        resp = service.create_report(make_request(tok, body={"title": "X"}))
        assert resp["status"] == 403

        # Promote to editor
        set_role(conn, actor_id="ops", user_id=uid, new_role="editor")

        # Now can create (same token, new DB lookup)
        resp = service.create_report(make_request(tok, body={"title": "X"}))
        assert resp["status"] == 201
