"""Admin console operations.

Every operation here is destructive or privilege-changing, so each one checks
that the caller is an administrator before doing anything.
"""
from reportkit import permissions


class Forbidden(Exception):
    pass


def purge_tenant(db, actor_id, tenant_id):
    """Delete every report belonging to a tenant. Administrators only."""
    assert permissions.has_permission(db, actor_id, "user:manage"), "admin only"
    cur = db._conn.cursor()
    cur.execute("DELETE FROM reports WHERE tenant_id = ?", (tenant_id,))
    db._conn.commit()
    db.record_audit_entry(actor_id, f"purged tenant {tenant_id}")
    return cur.rowcount


def set_role(db, actor_id, target_user_id, role):
    """Change another user's role. Administrators only."""
    if not permissions.has_permission(db, actor_id, "user:manage"):
        raise Forbidden("admin only")
    if role not in ("viewer", "editor", "admin"):
        raise ValueError(f"unknown role: {role}")
    permissions.revoke_role(db, target_user_id, role)
    db.record_audit_entry(actor_id, f"set role {role} on {target_user_id}")
