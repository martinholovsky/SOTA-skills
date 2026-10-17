"""Authentication and authorisation helpers."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .errors import AuthenticationError, AuthorisationError

# ---------------------------------------------------------------------------
# Role → permission mapping
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


def permissions_for_role(role: str) -> frozenset[str]:
    return _ROLE_PERMISSIONS.get(role, frozenset())


# ---------------------------------------------------------------------------
# Session resolution  (hot path — single JOIN query)
# ---------------------------------------------------------------------------

_RESOLVE_SQL = """
    SELECT
        u.id        AS user_id,
        u.tenant_id AS tenant_id,
        u.role      AS role,
        t.suspended AS suspended
    FROM sessions s
    JOIN users   u ON u.id        = s.user_id
    JOIN tenants t ON t.id        = u.tenant_id
    WHERE s.token = ?
      AND s.expires_at > ?
"""


def resolve_caller(conn: sqlite3.Connection, token: str) -> dict:
    """
    Resolve a bearer token to a caller dict.

    Returns:
        {user_id, tenant_id, role, permissions}

    Raises:
        AuthenticationError  – token missing / expired / unknown
        AuthorisationError   – tenant suspended
    """
    if not token:
        raise AuthenticationError("Missing bearer token.")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
    row = conn.execute(_RESOLVE_SQL, (token, now)).fetchone()
    if row is None:
        raise AuthenticationError("Invalid or expired token.")

    if row["suspended"]:
        raise AuthorisationError("Tenant account is suspended.")

    return {
        "user_id":     row["user_id"],
        "tenant_id":   row["tenant_id"],
        "role":        row["role"],
        "permissions": permissions_for_role(row["role"]),
    }


def require_permission(caller: dict, permission: str) -> None:
    """Raise AuthorisationError if *caller* lacks *permission*."""
    if permission not in caller["permissions"]:
        raise AuthorisationError(
            f"Permission denied: '{permission}' required."
        )


def extract_token(request: dict) -> str:
    """Pull the bearer token from request['headers']['Authorization']."""
    auth_header: str = (request.get("headers") or {}).get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return ""
