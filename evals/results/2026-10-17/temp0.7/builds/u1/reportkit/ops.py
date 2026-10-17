"""
Ops-console operations.

These functions are called by the internal ops console over the private network.
They are NOT exposed via the HTTP surface.

``purge_tenant`` and ``set_role`` both accept an *actor_id* so that the ops
console can record who initiated the action; currently we log it and could write
it to an audit table if required.
"""

from __future__ import annotations

import logging
import sqlite3

from reportkit.auth import _ROLE_PERMISSIONS

logger = logging.getLogger(__name__)

VALID_ROLES = frozenset(_ROLE_PERMISSIONS.keys())


class OpsError(Exception):
    pass


def purge_tenant(conn: sqlite3.Connection, actor_id: str, tenant_id: str) -> int:
    """
    Delete every report (and their attachments, via CASCADE) belonging to
    *tenant_id*.

    Returns the number of reports deleted.
    Raises :class:`OpsError` if the tenant does not exist.
    """
    row = conn.execute("SELECT id FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    if row is None:
        raise OpsError(f"Tenant '{tenant_id}' not found.")

    cursor = conn.execute(
        "DELETE FROM reports WHERE tenant_id = ?", (tenant_id,)
    )
    deleted = cursor.rowcount
    conn.commit()
    logger.info(
        "purge_tenant: actor=%s deleted %d reports for tenant=%s",
        actor_id,
        deleted,
        tenant_id,
    )
    return deleted


def set_role(
    conn: sqlite3.Connection,
    actor_id: str,
    user_id: str,
    new_role: str,
) -> None:
    """
    Change *user_id*'s role to *new_role*.

    Raises :class:`OpsError` for unknown roles or missing users.

    Note: because role resolution is cached at the session level (the query
    hits the DB on every request), the change takes effect on the next request
    made by the affected user — no cache invalidation is needed.
    """
    if new_role not in VALID_ROLES:
        raise OpsError(
            f"Invalid role '{new_role}'. Must be one of: {sorted(VALID_ROLES)}."
        )

    cursor = conn.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (new_role, user_id),
    )
    if cursor.rowcount == 0:
        raise OpsError(f"User '{user_id}' not found.")

    conn.commit()
    logger.info(
        "set_role: actor=%s changed user=%s to role=%s",
        actor_id,
        user_id,
        new_role,
    )
