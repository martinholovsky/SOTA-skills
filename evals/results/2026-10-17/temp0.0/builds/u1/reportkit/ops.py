"""
Internal ops-console operations.

These functions are called by the internal ops console, which runs inside
the private network.  They are NOT exposed over the public HTTP surface.

Both functions accept an *actor_id* so that audit logging can be added
without changing the call-site signature.
"""

from __future__ import annotations

import sqlite3

from .auth import AuthError, permissions_for_role
from .events import default_registry


def purge_tenant(conn: sqlite3.Connection, actor_id: str, tenant_id: str) -> dict:
    """
    Delete every report (and their attachments, via CASCADE) belonging to
    *tenant_id*.

    The actor must have the ``report:delete`` permission.  Because this is an
    internal console operation the actor's role is looked up directly rather
    than via a bearer token.
    """
    actor = conn.execute(
        "SELECT role FROM users WHERE id = ?", (actor_id,)
    ).fetchone()

    if actor is None:
        raise AuthError(f"Actor {actor_id!r} not found", status=403)

    if "report:delete" not in permissions_for_role(actor["role"]):
        raise AuthError(
            f"Actor {actor_id!r} lacks report:delete permission", status=403
        )

    # Fetch report ids before deletion so we can dispatch events
    report_ids = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM reports WHERE tenant_id = ?", (tenant_id,)
        ).fetchall()
    ]

    conn.execute("DELETE FROM reports WHERE tenant_id = ?", (tenant_id,))
    conn.commit()

    for rid in report_ids:
        default_registry.dispatch(
            "report.deleted",
            {"report_id": rid, "tenant_id": tenant_id, "deleted_by": actor_id},
        )

    return {"deleted_reports": len(report_ids), "tenant_id": tenant_id}


def set_role(
    conn: sqlite3.Connection,
    actor_id: str,
    target_user_id: str,
    new_role: str,
) -> dict:
    """
    Change *target_user_id*'s role to *new_role*.

    The actor must have the ``user:manage`` permission.
    Roles are changed from the internal ops console; the change takes effect
    on the next request because session resolution re-reads the role from the
    users table on every call.
    """
    valid_roles = {"viewer", "editor", "admin"}
    if new_role not in valid_roles:
        raise ValueError(f"Invalid role {new_role!r}; must be one of {valid_roles}")

    actor = conn.execute(
        "SELECT role FROM users WHERE id = ?", (actor_id,)
    ).fetchone()

    if actor is None:
        raise AuthError(f"Actor {actor_id!r} not found", status=403)

    if "user:manage" not in permissions_for_role(actor["role"]):
        raise AuthError(
            f"Actor {actor_id!r} lacks user:manage permission", status=403
        )

    result = conn.execute(
        "UPDATE users SET role = ? WHERE id = ?", (new_role, target_user_id)
    )
    conn.commit()

    if result.rowcount == 0:
        raise ValueError(f"User {target_user_id!r} not found")

    return {"user_id": target_user_id, "new_role": new_role}
