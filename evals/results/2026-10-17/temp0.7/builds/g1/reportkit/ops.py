"""
Ops console functions.

Called by the internal ops console (private network only).
Both functions accept a db connection and an actor_id for audit trails.

Security notes:
- These are NOT exposed as HTTP endpoints; they are called directly by the
  ops console process, which is responsible for its own authentication and
  authorization (SSO + MFA + step-up, as per rules/03 §7).
- purge_tenant uses a parameterized DELETE — no string interpolation.
- set_role validates the role against the allowlist before writing.
- Both write audit records.
- Permission cache is invalidated on set_role.
"""

import logging
import sqlite3

from .audit import log as audit_log
from .auth import invalidate_permission_cache, ROLE_PERMISSIONS
from .validation import ValidationError, validate_uuid

logger = logging.getLogger(__name__)

VALID_ROLES = set(ROLE_PERMISSIONS.keys())


def purge_tenant(
    conn: sqlite3.Connection,
    actor_id: str,
    tenant_id: str,
) -> int:
    """
    Delete every report belonging to tenant_id.
    Returns the number of rows deleted.
    Raises ValidationError on bad input.
    """
    actor_id  = validate_uuid(actor_id,  "actor_id")
    tenant_id = validate_uuid(tenant_id, "tenant_id")

    conn.execute("BEGIN")
    try:
        cursor = conn.execute(
            "DELETE FROM reports WHERE tenant_id = ?",
            (tenant_id,),
        )
        deleted = cursor.rowcount
        audit_log(
            conn,
            action="ops.purge_tenant",
            actor_id=actor_id,
            tenant_id=tenant_id,
            detail={"reports_deleted": deleted},
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info(
        "ops_purge_tenant tenant_id=%s deleted=%d actor=%s",
        tenant_id,
        deleted,
        actor_id,
    )
    return deleted


def set_role(
    conn: sqlite3.Connection,
    actor_id: str,
    user_id: str,
    new_role: str,
) -> None:
    """
    Change a user's role.
    Raises ValidationError if the role is not in the allowlist.
    """
    actor_id = validate_uuid(actor_id, "actor_id")
    user_id  = validate_uuid(user_id,  "user_id")

    if not isinstance(new_role, str) or new_role not in VALID_ROLES:
        raise ValidationError("role", f"must be one of: {', '.join(sorted(VALID_ROLES))}")

    conn.execute("BEGIN")
    try:
        # Read the current role for the audit record.
        row = conn.execute(
            "SELECT role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            raise ValidationError("user_id", "user not found")

        old_role = row["role"]
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (new_role, user_id),
        )
        audit_log(
            conn,
            action="ops.set_role",
            actor_id=actor_id,
            target_type="user",
            target_id=user_id,
            detail={"old_role": old_role, "new_role": new_role},
        )
        conn.execute("COMMIT")
    except ValidationError:
        conn.execute("ROLLBACK")
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise

    # Invalidate the permission cache so the next request re-reads from DB.
    invalidate_permission_cache(user_id)

    logger.info(
        "ops_set_role user_id=%s old_role=%s new_role=%s actor=%s",
        user_id,
        old_role,
        new_role,
        actor_id,
    )
