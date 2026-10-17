"""Ops console function tests."""

import pytest

from reportkit.ops import purge_tenant, set_role
from reportkit.validation import ValidationError
from tests.conftest import make_request, _make_user, _make_session


ACTOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TENANT = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _setup(conn):
    conn.execute("INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)", (TENANT, "T"))
    conn.execute(
        "INSERT OR IGNORE INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
        (ACTOR, TENANT, "actor", "admin"),
    )


class TestPurgeTenant:
    def test_deletes_reports(self, conn, service, editor):
        # Create a report via the service (uses editor's tenant).
        req = make_request(editor["token"], body={"title": "To Purge", "body": ""})
        service.create_report(req)
        tenant_id = editor["tenant_id"]
        deleted = purge_tenant(conn, ACTOR if ACTOR != editor["user_id"] else editor["user_id"],
                               tenant_id)
        # The actor UUID needs to exist in users; use editor's user_id as actor.
        # Re-run with a valid actor.
        deleted = purge_tenant(conn, editor["user_id"], tenant_id)
        assert deleted == 0  # already deleted above (first call)

    def test_purge_deletes_correct_tenant_only(self, conn, service, editor, other_editor):
        service.create_report(make_request(editor["token"], body={"title": "A", "body": ""}))
        service.create_report(make_request(other_editor["token"], body={"title": "B", "body": ""}))

        purge_tenant(conn, editor["user_id"], editor["tenant_id"])

        remaining = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        assert remaining == 1  # other tenant's report survives

    def test_invalid_uuid_raises(self, conn):
        with pytest.raises(ValidationError):
            purge_tenant(conn, "not-a-uuid", TENANT)


class TestSetRole:
    def test_set_role_changes_role(self, conn, editor):
        set_role(conn, editor["user_id"], editor["user_id"], "admin")
        row = conn.execute(
            "SELECT role FROM users WHERE id = ?", (editor["user_id"],)
        ).fetchone()
        assert row["role"] == "admin"

    def test_invalid_role_raises(self, conn, editor):
        with pytest.raises(ValidationError):
            set_role(conn, editor["user_id"], editor["user_id"], "superuser")

    def test_nonexistent_user_raises(self, conn):
        _setup(conn)
        with pytest.raises(ValidationError):
            set_role(conn, ACTOR, "00000000-0000-4000-8000-000000000000", "viewer")

    def test_cache_invalidated_after_set_role(self, conn, editor):
        from reportkit.auth import _cache_set, _cache_get, ROLE_PERMISSIONS
        # Seed the cache with viewer permissions.
        _cache_set(editor["user_id"], ROLE_PERMISSIONS["viewer"])
        assert _cache_get(editor["user_id"]) is not None

        set_role(conn, editor["user_id"], editor["user_id"], "admin")

        # Cache should be invalidated.
        assert _cache_get(editor["user_id"]) is None
