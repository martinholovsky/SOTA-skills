"""
Internal ops-console operations.

These functions are called by the internal ops console over the private
network.  They do NOT go through the HTTP surface and do NOT require a
bearer token; the console is responsible for its own access control.

Both functions accept an ``actor_id`` for audit purposes (future audit
log table not yet implemented — see NOTES.md).
"""

import logging
import sqlite3

from .errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

_VALID_ROLES = {"viewer", "editor", "admin"}


def purge_tenant(
    conn: sqlite3.Connection,
    actor_id: str,
    tenant_id: str,
) -> int:
    """
    Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    Raises NotFoundError if the tenant does not exist.
    """
    row = conn.execute(
        "SELECT id FROM tenants WHERE id = ?", (tenant_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Tenant '{tenant_id}' not found.")

    cursor = conn.execute(
        "DELETE FROM reports WHERE tenant_id = ?", (tenant_id,)
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
    new_role: str,
) -> None:
    """
    Change *user_id*'s role to *new_role*.

    Raises ValidationError for unknown roles, NotFoundError if the user
    does not exist.
    """
    if new_role not in _VALID_ROLES:
        raise ValidationError(
            f"Invalid role '{new_role}'. Must be one of: {sorted(_VALID_ROLES)}."
        )

    cursor = conn.execute(
        "UPDATE users SET role = ? WHERE id = ?", (new_role, user_id)
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise NotFoundError(f"User '{user_id}' not found.")

    logger.info(
        "set_role: actor=%s user=%s new_role=%s", actor_id, user_id, new_role
    )
