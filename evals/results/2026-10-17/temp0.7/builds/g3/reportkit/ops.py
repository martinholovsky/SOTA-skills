"""
Internal ops-console functions.

These are called by the internal ops console (private network only) and
are NOT exposed through the HTTP surface.  They write an immutable audit
log entry for every mutation.

Neither function accepts tenant_id or actor_id from user-controlled
request data; callers pass them from their own authenticated session.
"""

import json
import logging
import uuid

logger = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"viewer", "editor", "admin"})


def purge_tenant(conn, actor_id: str, tenant_id: str) -> int:
    """
    Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    Writes an audit log entry.
    Raises ValueError for invalid arguments.
    """
    if not actor_id or not isinstance(actor_id, str):
        raise ValueError("actor_id must be a non-empty string")
    if not tenant_id or not isinstance(tenant_id, str):
        raise ValueError("tenant_id must be a non-empty string")

    with conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM reports WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        count = row["n"] if row else 0

        conn.execute(
            "DELETE FROM reports WHERE tenant_id = ?",
            (tenant_id,),
        )

        _write_audit(
            conn,
            actor_id=actor_id,
            action="purge_tenant",
            target_type="tenant",
            target_id=tenant_id,
            detail={"reports_deleted": count},
        )

    logger.info(
        "ops.purge_tenant",
        extra={
            "actor_id":        actor_id,
            "tenant_id":       tenant_id,
            "reports_deleted": count,
        },
    )
    return count


def set_role(conn, actor_id: str, target_user_id: str, new_role: str) -> None:
    """
    Change *target_user_id*'s role to *new_role*.

    Raises ValueError for invalid arguments or unknown user.
    Writes an audit log entry.
    """
    if not actor_id or not isinstance(actor_id, str):
        raise ValueError("actor_id must be a non-empty string")
    if not target_user_id or not isinstance(target_user_id, str):
        raise ValueError("target_user_id must be a non-empty string")
    if new_role not in _VALID_ROLES:
        raise ValueError(f"new_role must be one of {sorted(_VALID_ROLES)}")

    with conn:
        row = conn.execute(
            "SELECT role FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"user {target_user_id!r} not found")

        old_role = row["role"]

        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (new_role, target_user_id),
        )

        _write_audit(
            conn,
            actor_id=actor_id,
            action="set_role",
            target_type="user",
            target_id=target_user_id,
            detail={"old_role": old_role, "new_role": new_role},
        )

    logger.info(
        "ops.set_role",
        extra={
            "actor_id":        actor_id,
            "target_user_id":  target_user_id,
            "old_role":        old_role,
            "new_role":        new_role,
        },
    )


def _write_audit(
    conn,
    *,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (actor_id, action, target_type, target_id, detail)
             VALUES (?, ?, ?, ?, ?)
        """,
        (actor_id, action, target_type, target_id, json.dumps(detail)),
    )
