"""Permission cache stale-detection tests."""

import pytest
from tests.conftest import _make_user, _req
from reportkit.auth import get_permissions
from reportkit.service import ReportService


def test_cache_populated_on_first_call(db):
    _, uid, _ = _make_user(db, role="editor")
    perms = get_permissions(db, uid, "editor")
    assert "report:write" in perms

    row = db.execute(
        "SELECT * FROM permission_cache WHERE user_id=?", (uid,)
    ).fetchone()
    assert row is not None
    assert row["role_at"] == "editor"


def test_cache_invalidated_on_role_change(db, svc):
    from reportkit.ops import set_role
    import uuid
    actor_id = str(uuid.uuid4())
    tid, uid, raw = _make_user(db, role="viewer")

    # Warm cache
    svc.list_reports(_req(raw))

    # Promote to editor
    set_role(db, actor_id, tid, uid, "editor")

    # Cache should be gone
    row = db.execute(
        "SELECT * FROM permission_cache WHERE user_id=?", (uid,)
    ).fetchone()
    assert row is None


def test_stale_cache_recomputed(db):
    """If role_at doesn't match current role, cache is recomputed."""
    _, uid, _ = _make_user(db, role="viewer")

    # Manually insert a stale cache entry for a different role
    db.execute(
        "INSERT INTO permission_cache(user_id, permissions, role_at) VALUES (?,?,?)",
        (uid, '["report:read","report:write"]', "editor"),
    )
    db.commit()

    # get_permissions with current role "viewer" should recompute
    perms = get_permissions(db, uid, "viewer")
    assert "report:write" not in perms
    assert "report:read" in perms
