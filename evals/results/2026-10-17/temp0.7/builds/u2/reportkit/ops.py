"""Internal ops-console operations.

These functions are called by the internal ops console which runs inside the
private network.  They receive an explicit db connection and actor_id (for
audit purposes) rather than going through the HTTP surface.

purge_tenant  — delete every report (and cascade to attachments) for a tenant
set_role      — change a user's role; only admins may call this via the console
"""

import sqlite3

from .errors import NotFoundError, ValidationError

_VALID_ROLES = {"viewer", "editor", "admin"}


def purge_tenant(conn: sqlite3.Connection, actor_id: str, tenant_id: str) -> int:
    """Delete all reports (and cascading attachments) for *tenant_id*.

    Returns the number of reports deleted.  Does NOT delete the tenant row
    itself — that is a separate lifecycle decision.

    Raises NotFoundError if the tenant does not exist.
    """
    row = conn.execute(
        "SELECT id FROM tenants WHERE id = ?", (tenant_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Tenant '{tenant_id}' not found")

    cursor = conn.execute(
        "DELETE FROM reports WHERE tenant_id = ?", (tenant_id,)
    )
    conn.commit()
    return cursor.rowcount


def set_role(
    conn: sqlite3.Connection,
    actor_id: str,
    user_id: str,
    new_role: str,
) -> None:
    """Set *user_id*'s role to *new_role*.

    Raises ValidationError for an unknown role, NotFoundError if the user
    does not exist.
    """
    if new_role not in _VALID_ROLES:
        raise ValidationError(
            f"Invalid role '{new_role}'. Must be one of: {', '.join(sorted(_VALID_ROLES))}"
        )

    row = conn.execute(
        "SELECT id FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"User '{user_id}' not found")

    conn.execute(
        "UPDATE users SET role = ? WHERE id = ?", (new_role, user_id)
    )
    conn.commit()
