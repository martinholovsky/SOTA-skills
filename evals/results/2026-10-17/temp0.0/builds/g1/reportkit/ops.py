"""Internal ops-console operations.

These functions are called by the internal ops console over the private
network.  They are NOT exposed as HTTP endpoints.  Callers are authenticated
at the network/mTLS layer; we still validate inputs and write audit records.
"""

from __future__ import annotations

import logging
import sqlite3

from reportkit.errors import BadRequest, NotFound
from reportkit.logging_utils import get_logger, log_security_event
from reportkit.validation import require_uuid, validate_role

_log = get_logger(__name__)


def purge_tenant(conn: sqlite3.Connection, actor_id: str, tenant_id: str) -> int:
    """Delete every report belonging to *tenant_id*.

    Returns the number of reports deleted.
    Raises BadRequest on invalid UUIDs, NotFound if the tenant does not exist.
    """
    actor_id = require_uuid(actor_id, "actor_id")
    tenant_id = require_uuid(tenant_id, "tenant_id")

    tenant = conn.execute(
        "SELECT id FROM tenants WHERE id = ?", (tenant_id,)
    ).fetchone()
    if tenant is None:
        raise NotFound("tenant not found")

    with conn:
        cur = conn.execute(
            "DELETE FROM reports WHERE tenant_id = ?", (tenant_id,)
        )
        deleted = cur.rowcount

    log_security_event(
        _log,
        event="ops.purge_tenant",
        user_id=actor_id,
        tenant_id=tenant_id,
        action="purge_tenant",
        target_type="tenant",
        target_id=tenant_id,
        detail={"reports_deleted": deleted},
        level=logging.WARNING,
    )
    return deleted


def set_role(
    conn: sqlite3.Connection, actor_id: str, tenant_id: str, user_id: str, role: str
) -> None:
    """Change *user_id*'s role within *tenant_id* to *role*.

    Raises BadRequest on invalid inputs, NotFound if the user does not exist
    in the tenant.
    """
    actor_id = require_uuid(actor_id, "actor_id")
    tenant_id = require_uuid(tenant_id, "tenant_id")
    user_id = require_uuid(user_id, "user_id")
    role = validate_role(role)

    user = conn.execute(
        "SELECT id, role FROM users WHERE id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ).fetchone()
    if user is None:
        raise NotFound("user not found in tenant")

    old_role = user["role"]
    with conn:
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ? AND tenant_id = ?",
            (role, user_id, tenant_id),
        )

    log_security_event(
        _log,
        event="ops.set_role",
        user_id=actor_id,
        tenant_id=tenant_id,
        action="set_role",
        target_type="user",
        target_id=user_id,
        detail={"old_role": old_role, "new_role": role},
        level=logging.WARNING,
    )
