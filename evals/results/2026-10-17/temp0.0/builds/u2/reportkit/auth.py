"""Session resolution and permission helpers."""

import sqlite3
from typing import Optional

# ---------------------------------------------------------------------------
# Permission model
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


def permissions_for_role(role: str) -> frozenset[str]:
    try:
        return _ROLE_PERMISSIONS[role]
    except KeyError:
        return frozenset()


# ---------------------------------------------------------------------------
# Session / caller resolution
# ---------------------------------------------------------------------------

class AuthenticationError(Exception):
    """Raised when a bearer token cannot be resolved to a live session."""


class AuthorizationError(Exception):
    """Raised when the resolved caller lacks a required permission."""


def _extract_token(request: dict) -> str:
    """Pull the bearer token out of the Authorization header."""
    auth_header: str = (request.get("headers") or {}).get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    return auth_header[7:].strip()


def resolve_caller(conn: sqlite3.Connection, request: dict) -> dict:
    """
    Resolve the bearer token to a caller dict:

        {user_id, tenant_id, email, role, permissions}

    The query joins sessions → users → roles in one round-trip.  An index on
    (user_id, tenant_id) in the roles table keeps this fast even as the user
    table grows (see schema.sql idx_roles_user_tenant).
    """
    token = _extract_token(request)

    row = conn.execute(
        """
        SELECT
            u.id        AS user_id,
            u.tenant_id AS tenant_id,
            u.email     AS email,
            r.role      AS role,
            t.suspended AS suspended
        FROM sessions s
        JOIN users   u ON u.id        = s.user_id
        JOIN tenants t ON t.id        = u.tenant_id
        LEFT JOIN roles r
               ON r.user_id   = u.id
              AND r.tenant_id = u.tenant_id
        WHERE s.token      = ?
          AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        (token,),
    ).fetchone()

    if row is None:
        raise AuthenticationError("Invalid or expired session token.")

    if row["suspended"]:
        raise AuthorizationError("Tenant account is suspended.")

    role = row["role"] or "viewer"
    return {
        "user_id":     row["user_id"],
        "tenant_id":   row["tenant_id"],
        "email":       row["email"],
        "role":        role,
        "permissions": permissions_for_role(role),
    }


def require_permission(caller: dict, permission: str) -> None:
    """Raise AuthorizationError if *caller* does not hold *permission*."""
    if permission not in caller["permissions"]:
        raise AuthorizationError(
            f"Permission denied: {permission!r} required, "
            f"caller holds {sorted(caller['permissions'])}."
        )
