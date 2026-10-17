"""
Authentication and authorization.

- Resolves a session token to a user + permissions.
- Permission cache with TTL to avoid joining three tables on every hot list request.
- Authorization checks: deny-by-default.
"""

import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import NamedTuple

from .crypto import hash_token
from .validation import ValidationError, validate_uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permission model
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}

# ---------------------------------------------------------------------------
# Permission cache
# ---------------------------------------------------------------------------

# Simple in-process TTL cache: {user_id: (permissions_frozenset, expiry_epoch)}
# Roles are changed from the ops console; a 30-second TTL is a reasonable
# trade-off between hot-path performance and revocation latency.
_PERM_CACHE: dict[str, tuple[frozenset[str], float]] = {}
_PERM_CACHE_TTL = 30.0  # seconds


def _cache_get(user_id: str) -> frozenset[str] | None:
    entry = _PERM_CACHE.get(user_id)
    if entry is None:
        return None
    perms, expiry = entry
    if time.monotonic() > expiry:
        _PERM_CACHE.pop(user_id, None)
        return None
    return perms


def _cache_set(user_id: str, perms: frozenset[str]) -> None:
    _PERM_CACHE[user_id] = (perms, time.monotonic() + _PERM_CACHE_TTL)


def invalidate_permission_cache(user_id: str) -> None:
    """Call this whenever a role changes so the cache does not serve stale data."""
    _PERM_CACHE.pop(user_id, None)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

class Principal(NamedTuple):
    user_id: str
    tenant_id: str
    role: str
    permissions: frozenset[str]


class AuthError(Exception):
    """Authentication or authorization failure."""
    def __init__(self, message: str, status: int = 401):
        self.status = status
        super().__init__(message)


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------

def resolve_session(conn: sqlite3.Connection, token: str) -> Principal:
    """
    Resolve a bearer token to a Principal.

    1. Hash the token (tokens are high-entropy; SHA-256 is sufficient).
    2. Look up the session; reject if absent or expired.
    3. Return the principal with permissions (cache-assisted).

    Raises AuthError on any failure.
    """
    token_hash = hash_token(token)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Single parameterized query — no string interpolation.
    row = conn.execute(
        """
        SELECT s.user_id, u.tenant_id, u.role
        FROM   sessions s
        JOIN   users    u ON u.id = s.user_id
        WHERE  s.token_hash = ?
          AND  s.expires_at > ?
        """,
        (token_hash, now_iso),
    ).fetchone()

    if row is None:
        raise AuthError("invalid or expired session", status=401)

    user_id   = row["user_id"]
    tenant_id = row["tenant_id"]
    role      = row["role"]

    # Permissions: try cache first, then derive from role.
    # The role already comes from the DB join above; if the cache holds a
    # *different* role it means a change happened within the TTL window.
    # We derive from the freshly-read role, then cache that.
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    _cache_set(user_id, perms)

    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        permissions=perms,
    )


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def require_permission(principal: Principal, permission: str) -> None:
    """
    Deny-by-default: raise AuthError(403) if the principal lacks the permission.
    This is the single authorization API; callers must use it and return
    immediately on failure (never fall through).
    """
    if permission not in principal.permissions:
        raise AuthError(
            f"permission denied: {permission}",
            status=403,
        )


def require_tenant_owner(principal: Principal, resource_tenant_id: str) -> None:
    """
    Verify the principal belongs to the resource's tenant.
    Combined with require_permission this enforces both RBAC and tenant isolation.
    """
    if principal.tenant_id != resource_tenant_id:
        # Return 404 to avoid leaking that the resource exists in another tenant.
        raise AuthError("report not found", status=404)
