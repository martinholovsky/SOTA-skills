"""
Internal ops-console operations.

These functions are called by the ops console, which runs inside the private
network.  They are NOT exposed over the public HTTP surface.

purge_tenant  — delete every report belonging to a tenant.
set_role      — change a user's role within a tenant.

Both functions accept an actor_id for audit purposes; in a fuller
implementation this would write to an audit log table.
"""

from __future__ import annotations

import logging
import sqlite3

from reportkit.auth import permissions_for_role

logger = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"viewer", "editor", "admin"})


def purge_tenant(
    conn: sqlite3.Connection,
    actor_id: str,
    tenant_id: str,
) -> int:
    """
    Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    Cascading deletes in the schema remove associated attachments automatically.
    """
    cursor = conn.execute(
        "DELETE FROM reports WHERE tenant_id = ?",
        (tenant_id,),
    )
    conn.commit()
    count = cursor.rowcount
    logger.info(
        "purge_tenant: actor=%s tenant=%s deleted_reports=%d",
        actor_id, tenant_id, count,
    )
    return count


def set_role(
    conn: sqlite3.Connection,
    actor_id: str,
    user_id: str,
    tenant_id: str,
    new_role: str,
) -> None:
    """
    Set *user_id*'s role within *tenant_id* to *new_role*.

    Raises ValueError for an unrecognised role name.
    """
    if new_role not in _VALID_ROLES:
        raise ValueError(
            f"Unknown role {new_role!r}. Valid roles: {sorted(_VALID_ROLES)}"
        )

    conn.execute(
        """
        INSERT INTO roles (user_id, tenant_id, role)
        VALUES (?, ?, ?)
        ON CONFLICT (user_id, tenant_id) DO UPDATE SET role = excluded.role
        """,
        (user_id, tenant_id, new_role),
    )
    conn.commit()
    logger.info(
        "set_role: actor=%s user=%s tenant=%s role=%s",
        actor_id, user_id, tenant_id, new_role,
    )
