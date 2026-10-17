"""
Tests for ops-console operations: purge_tenant, set_role.
"""

import uuid

import pytest

from reportkit.errors import BadRequest, NotFound
from reportkit.ops import purge_tenant, set_role
from tests.conftest import make_user, auth_headers


def _uuid():
    return str(uuid.uuid4())


class TestPurgeTenant:
    def test_purge_deletes_reports(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "R1", "body": ""},
        })
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "R2", "body": ""},
        })
        actor_id = _uuid()
        # actor must exist as a user for FK; insert a minimal one.
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_a),
        )
        db.commit()
        deleted = purge_tenant(db, actor_id, tenant_a)
        assert deleted == 2
        rows = db.execute(
            "SELECT id FROM reports WHERE tenant_id = ?", (tenant_a,)
        ).fetchall()
        assert rows == []

    def test_purge_nonexistent_tenant_raises(self, db):
        actor_id = _uuid()
        db.execute(
            "INSERT INTO tenants (id) VALUES (?)", (_uuid(),)
        )
        db.commit()
        with pytest.raises(NotFound):
            purge_tenant(db, actor_id, _uuid())

    def test_purge_invalid_uuid_raises(self, db):
        with pytest.raises(BadRequest):
            purge_tenant(db, "not-a-uuid", "also-not-a-uuid")

    def test_purge_does_not_affect_other_tenant(self, service, db, tenant_a, tenant_b):
        _, token_a = make_user(db, tenant_a, "editor")
        _, token_b = make_user(db, tenant_b, "editor")
        service.create_report({
            "headers": auth_headers(token_a),
            "body": {"title": "Tenant A", "body": ""},
        })
        service.create_report({
            "headers": auth_headers(token_b),
            "body": {"title": "Tenant B", "body": ""},
        })
        actor_id = _uuid()
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_a),
        )
        db.commit()
        purge_tenant(db, actor_id, tenant_a)
        rows = db.execute(
            "SELECT id FROM reports WHERE tenant_id = ?", (tenant_b,)
        ).fetchall()
        assert len(rows) == 1


class TestSetRole:
    def test_set_role_changes_role(self, db, tenant_a):
        user_id, _ = make_user(db, tenant_a, "viewer")
        actor_id = _uuid()
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_a),
        )
        db.commit()
        set_role(db, actor_id, tenant_a, user_id, "editor")
        row = db.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        assert row["role"] == "editor"

    def test_set_invalid_role_raises(self, db, tenant_a):
        user_id, _ = make_user(db, tenant_a, "viewer")
        actor_id = _uuid()
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_a),
        )
        db.commit()
        with pytest.raises(BadRequest):
            set_role(db, actor_id, tenant_a, user_id, "superuser")

    def test_set_role_nonexistent_user_raises(self, db, tenant_a):
        actor_id = _uuid()
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_a),
        )
        db.commit()
        with pytest.raises(NotFound):
            set_role(db, actor_id, tenant_a, _uuid(), "editor")

    def test_set_role_wrong_tenant_raises(self, db, tenant_a, tenant_b):
        user_id, _ = make_user(db, tenant_a, "viewer")
        actor_id = _uuid()
        db.execute(
            "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, 'admin')",
            (actor_id, tenant_b),
        )
        db.commit()
        with pytest.raises(NotFound):
            set_role(db, actor_id, tenant_b, user_id, "editor")
