"""
Internal ops-console functions.

Rules applied
-------------
- rules/03 §7: admin tools have tiered roles, MFA/step-up (enforced by the
  ops console caller; documented in NOTES.md), and immutable audit trails.
- rules/03 §2: ownership predicate in purge_tenant.
- rules/03 §3: set_role invalidates the permission cache immediately.
- rules/01 §1: all inputs validated.
- These functions are called by the ops console inside the private network;
  they do NOT go through the HTTP surface and therefore do NOT call
  authenticate() — the ops console is responsible for its own authn/authz.
  The actor_id is passed in explicitly and written to the audit log.
"""

import logging

from .audit import log as audit_log
from .validation import validate_uuid, validate_role

logger = logging.getLogger(__name__)


def purge_tenant(db, actor_id: str, tenant_id: str) -> int:
    """
    Delete every report belonging to tenant_id.

    Returns the number of reports deleted.
    actor_id is the ops-console user performing the action; written to
    the audit log but not validated as a DB foreign key (the ops console
    may use its own identity system).
    """
    actor_id  = validate_uuid(actor_id,  "actor_id")
    tenant_id = validate_uuid(tenant_id, "tenant_id")

    cursor = db.execute(
        "DELETE FROM reports WHERE tenant_id = ?",
        (tenant_id,),
    )
    count = cursor.rowcount

    audit_log(
        db,
        "ops.tenant_purged",
        actor_id=actor_id,
        tenant_id=tenant_id,
        detail={"reports_deleted": count},
    )
    db.commit()

    logger.info(
        "tenant_purged",
        extra={"tenant_id": tenant_id, "actor_id": actor_id, "count": count},
    )
    return count


def set_role(db, actor_id: str, tenant_id: str, user_id: str, new_role: str) -> None:
    """
    Change a user's role and immediately invalidate the permission cache.

    Raises ValueError if the user does not exist in the given tenant.
    """
    actor_id  = validate_uuid(actor_id,  "actor_id")
    tenant_id = validate_uuid(tenant_id, "tenant_id")
    user_id   = validate_uuid(user_id,   "user_id")
    new_role  = validate_role(new_role,  "new_role")

    cursor = db.execute(
        """
        UPDATE users
           SET role = ?
         WHERE id        = ?
           AND tenant_id = ?
        """,
        (new_role, user_id, tenant_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"User {user_id!r} not found in tenant {tenant_id!r}")

    # Invalidate the permission cache so the next request recomputes it
    # (rules/03 §3: stale session privilege)
    db.execute(
        "DELETE FROM permission_cache WHERE user_id = ?",
        (user_id,),
    )

    audit_log(
        db,
        "ops.role_changed",
        actor_id=actor_id,
        tenant_id=tenant_id,
        target_id=user_id,
        detail={"new_role": new_role},
    )
    db.commit()

    logger.info(
        "role_changed",
        extra={
            "user_id":   user_id,
            "tenant_id": tenant_id,
            "new_role":  new_role,
            "actor_id":  actor_id,
        },
    )
