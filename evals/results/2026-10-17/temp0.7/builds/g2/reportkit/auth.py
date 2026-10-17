"""
Authentication and permission resolution.

Rules applied
-------------
- rules/02 §8: bearer tokens hashed at rest; constant-time comparison.
- rules/03 §1: deny by default; permissions from server-side state only.
- rules/03 §3: permission cache with stale-detection; never from request body.
- rules/02 §1: session expiry enforced.
"""

import json
import time
import logging

from .crypto import hash_token
from .models import ROLE_PERMISSIONS

logger = logging.getLogger(__name__)

SESSION_EXPIRY_SECONDS = 3600   # 1 hour


class AuthError(Exception):
    """Raised when authentication or authorisation fails."""
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


def _extract_bearer(request: dict) -> str:
    """Pull the raw token from Authorization: Bearer <token>."""
    auth = request.get("headers", {}).get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthError("Missing or malformed Authorization header")
    token = auth[len("Bearer "):]
    if not token:
        raise AuthError("Empty bearer token")
    return token


def authenticate(db, request: dict) -> dict:
    """
    Resolve the bearer token to a user record.

    Returns a dict with keys: user_id, tenant_id, role, username.
    Raises AuthError on any failure (expired, unknown, tenant suspended).
    """
    raw_token = _extract_bearer(request)
    token_hash = hash_token(raw_token)
    now = int(time.time())

    row = db.execute(
        """
        SELECT s.user_id, s.tenant_id, s.expires_at,
               u.role, u.username,
               t.suspended
          FROM sessions s
          JOIN users   u ON u.id = s.user_id
          JOIN tenants t ON t.id = s.tenant_id
         WHERE s.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()

    if row is None:
        raise AuthError("Invalid or expired token")
    if row["expires_at"] < now:
        raise AuthError("Token expired")
    if row["suspended"]:
        raise AuthError("Tenant suspended", status=403)

    return {
        "user_id":   row["user_id"],
        "tenant_id": row["tenant_id"],
        "role":      row["role"],
        "username":  row["username"],
    }


def get_permissions(db, user_id: str, current_role: str) -> set:
    """
    Return the permission set for a user.

    Uses a permission_cache row if the cached role matches current_role;
    otherwise recomputes and writes the cache (stale-on-role-change detection).

    This is the hot path (called on every list_reports request).
    """
    row = db.execute(
        "SELECT permissions, role_at FROM permission_cache WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is not None and row["role_at"] == current_role:
        return set(json.loads(row["permissions"]))

    # Recompute from the authoritative role
    perms = set(ROLE_PERMISSIONS.get(current_role, []))
    db.execute(
        """
        INSERT INTO permission_cache(user_id, permissions, role_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE
           SET permissions = excluded.permissions,
               role_at     = excluded.role_at
        """,
        (user_id, json.dumps(sorted(perms)), current_role),
    )
    db.commit()
    return perms


def require_permission(db, principal: dict, permission: str) -> None:
    """
    Raise AuthError(403) if the principal lacks the required permission.

    Always fetches permissions from the server-side role; never trusts
    anything from the request.
    """
    perms = get_permissions(db, principal["user_id"], principal["role"])
    if permission not in perms:
        logger.warning(
            "access_denied",
            extra={
                "user_id":    principal["user_id"],
                "tenant_id":  principal["tenant_id"],
                "permission": permission,
            },
        )
        raise AuthError("Forbidden", status=403)
