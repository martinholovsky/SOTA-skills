"""Session resolution and permission checking."""

import sqlite3
from datetime import datetime, timezone

from .errors import AuthenticationError, PermissionError

# Role → frozenset of permissions
_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def resolve_caller(conn: sqlite3.Connection, token: str) -> dict:
    """Return caller info dict or raise AuthenticationError.

    Uses v_caller_permissions (the hot-path view) so a single query covers
    the session → user → tenant join.  The view is backed by indexes on
    sessions.user_id and users.tenant_id.
    """
    if not token:
        raise AuthenticationError("Missing bearer token")

    row = conn.execute(
        """
        SELECT user_id, tenant_id, role, tenant_suspended, expires_at
        FROM   v_caller_permissions
        WHERE  token = ?
        """,
        (token,),
    ).fetchone()

    if row is None:
        raise AuthenticationError("Invalid or expired token")

    if row["expires_at"] < _now_utc():
        raise AuthenticationError("Token has expired")

    if row["tenant_suspended"]:
        raise AuthenticationError("Tenant is suspended")

    return {
        "user_id":   row["user_id"],
        "tenant_id": row["tenant_id"],
        "role":      row["role"],
        "permissions": _ROLE_PERMISSIONS[row["role"]],
    }


def require_permission(caller: dict, permission: str) -> None:
    """Raise PermissionError if *caller* does not hold *permission*."""
    if permission not in caller["permissions"]:
        raise PermissionError(
            f"Role '{caller['role']}' does not grant '{permission}'"
        )


def _extract_token(request: dict) -> str:
    """Pull the bearer token out of request['headers']['Authorization']."""
    headers: dict = request.get("headers") or {}
    auth: str = headers.get("Authorization") or headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""
