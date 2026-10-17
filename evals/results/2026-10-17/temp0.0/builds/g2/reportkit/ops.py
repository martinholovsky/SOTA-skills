"""
Internal ops-console operations.

These functions are called by the internal ops console, which runs inside
the private network.  They are NOT exposed over HTTP.

Both functions write audit records before committing so the trail is
atomic with the mutation.
"""

import sqlite3

from .audit import record as audit_record
from .errors import NotFound, BadRequest
from .logging import get_logger
from .validation import require_uuid

logger = get_logger(__name__)

_VALID_ROLES = frozenset({"viewer", "editor", "admin"})


def purge_tenant(db: sqlite3.Connection, actor_id: str, tenant_id: str) -> int:
    """
    Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    Raises NotFound if the tenant does not exist.
    """
    require_uuid(actor_id, "actor_id")
    require_uuid(tenant_id, "tenant_id")

    row = db.execute(
        "SELECT id FROM tenants WHERE id = ?", (tenant_id,)
    ).fetchone()
    if row is None:
        raise NotFound(f"Tenant {tenant_id!r} not found")

    result = db.execute(
        "DELETE FROM reports WHERE tenant_id = ?", (tenant_id,)
    )
    deleted = result.rowcount

    audit_record(
        db,
        action="tenant.purge_reports",
        actor_id=actor_id,
        tenant_id=tenant_id,
        detail={"deleted_count": deleted},
    )
    db.commit()

    logger.info(
        "tenant_purged",
        extra={
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "deleted_count": deleted,
        },
    )
    return deleted


def set_role(
    db: sqlite3.Connection,
    actor_id: str,
    tenant_id: str,
    user_id: str,
    new_role: str,
) -> None:
    """
    Change *user_id*'s role to *new_role* within *tenant_id*.

    Raises NotFound if the user does not exist in that tenant.
    Raises BadRequest if *new_role* is not a valid role.
    """
    require_uuid(actor_id, "actor_id")
    require_uuid(tenant_id, "tenant_id")
    require_uuid(user_id, "user_id")

    if new_role not in _VALID_ROLES:
        raise BadRequest(
            f"Invalid role {new_role!r}; must be one of "
            f"{', '.join(sorted(_VALID_ROLES))}"
        )

    row = db.execute(
        "SELECT role FROM users WHERE id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ).fetchone()
    if row is None:
        raise NotFound(f"User {user_id!r} not found in tenant {tenant_id!r}")

    old_role = row["role"]
    db.execute(
        "UPDATE users SET role = ? WHERE id = ? AND tenant_id = ?",
        (new_role, user_id, tenant_id),
    )

    audit_record(
        db,
        action="user.set_role",
        actor_id=actor_id,
        tenant_id=tenant_id,
        target_type="user",
        target_id=user_id,
        detail={"old_role": old_role, "new_role": new_role},
    )
    db.commit()

    logger.info(
        "role_changed",
        extra={
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "old_role": old_role,
            "new_role": new_role,
        },
    )
