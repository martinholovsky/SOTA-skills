"""
Authentication and permission resolution.

Token → session → user → role → permission set.

The permission cache is an in-process dict keyed by (user_id, role).
Roles are changed from the ops console; the cache entry is invalidated
when set_role() is called.  TTL is a safety net.
"""

import hashlib
import time
import sqlite3
from typing import Optional

from .errors import Unauthorized, Forbidden, TenantSuspended
from .logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Permission model
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write",
                         "report:delete", "user:manage"}),
}


def permissions_for_role(role: str) -> frozenset:
    return _ROLE_PERMISSIONS.get(role, frozenset())


# ---------------------------------------------------------------------------
# Token hashing — SHA-256 is fine for high-entropy bearer tokens (rules/02 §8).
# ---------------------------------------------------------------------------

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------

class Principal:
    """Resolved, authenticated caller."""

    __slots__ = ("user_id", "tenant_id", "role", "permissions")

    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.permissions: frozenset = permissions_for_role(role)

    def require(self, permission: str) -> None:
        """Raise Forbidden if the caller lacks *permission*."""
        if permission not in self.permissions:
            raise Forbidden(
                f"Permission '{permission}' required; caller has role '{self.role}'"
            )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Principal(user_id={self.user_id!r}, "
            f"tenant_id={self.tenant_id!r}, role={self.role!r})"
        )


def resolve_principal(db: sqlite3.Connection, token: str) -> Principal:
    """
    Resolve a bearer token to a Principal.

    Raises Unauthorized on any failure so callers cannot distinguish
    "no such token" from "expired" (account enumeration, rules/02 §1).
    """
    if not token or not isinstance(token, str):
        raise Unauthorized("Missing bearer token")

    # Length-cap: tokens are UUIDs or similar; reject absurdly long strings.
    if len(token) > 512:
        raise Unauthorized("Token too long")

    token_hash = hash_token(token)
    now_iso = _utcnow_iso()

    row = db.execute(
        """
        SELECT s.user_id, s.expires_at,
               u.tenant_id, u.role,
               t.suspended
        FROM   sessions s
        JOIN   users   u ON u.id = s.user_id
        JOIN   tenants t ON t.id = u.tenant_id
        WHERE  s.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()

    if row is None:
        logger.warning("auth_failure", extra={"reason": "token_not_found"})
        raise Unauthorized("Invalid or expired token")

    if row["expires_at"] < now_iso:
        logger.warning("auth_failure", extra={"reason": "token_expired"})
        raise Unauthorized("Invalid or expired token")

    if row["suspended"]:
        raise TenantSuspended("Tenant is suspended")

    return Principal(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        role=row["role"],
    )


def _utcnow_iso() -> str:
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
