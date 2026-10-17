"""Internal ops-console operations.

These functions are called by the internal ops console, which runs inside the
private network.  They intentionally bypass HTTP auth; the caller is trusted.
"""
import sqlite3
import uuid
from datetime import datetime, timezone

from .auth import Caller, PermissionError
from . import events


def purge_tenant(
    conn: sqlite3.Connection,
    actor_id: str,
    tenant_id: str,
) -> int:
    """Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    The actor must be an admin of the target tenant OR an ops-console caller
    (represented here by passing actor_id=None to skip the check).
    """
    # When called from the ops console, actor_id may be None (trusted caller).
    if actor_id is not None:
        row = conn.execute(
            "SELECT role FROM users WHERE id = ? AND tenant_id = ?",
            (actor_id, tenant_id),
        ).fetchone()
        if row is None or row["role"] != "admin":
            raise PermissionError("Only admins may purge a tenant's reports")

    rows = conn.execute(
        "SELECT id FROM reports WHERE tenant_id = ?", (tenant_id,)
    ).fetchall()
    report_ids = [r["id"] for r in rows]

    conn.execute("DELETE FROM reports WHERE tenant_id = ?", (tenant_id,))
    conn.commit()

    for rid in report_ids:
        events.dispatch(
            "report.deleted",
            {"report_id": rid, "tenant_id": tenant_id, "actor_id": actor_id},
        )

    return len(report_ids)


def set_role(
    conn: sqlite3.Connection,
    actor_id: str | None,
    tenant_id: str,
    target_user_id: str,
    new_role: str,
) -> None:
    """Change *target_user_id*'s role within *tenant_id*.

    Roles are changed from the ops console; actor_id=None means trusted caller.
    """
    valid_roles = ("viewer", "editor", "admin")
    if new_role not in valid_roles:
        raise ValueError(f"role must be one of {valid_roles}")

    if actor_id is not None:
        row = conn.execute(
            "SELECT role FROM users WHERE id = ? AND tenant_id = ?",
            (actor_id, tenant_id),
        ).fetchone()
        if row is None or row["role"] != "admin":
            raise PermissionError("Only admins may change roles")

    result = conn.execute(
        """
        UPDATE users SET role = ?
        WHERE id = ? AND tenant_id = ?
        """,
        (new_role, target_user_id, tenant_id),
    )
    conn.commit()
    if result.rowcount == 0:
        raise ValueError(
            f"User {target_user_id} not found in tenant {tenant_id}"
        )
