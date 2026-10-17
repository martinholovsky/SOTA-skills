"""Authentication and authorisation helpers."""

from __future__ import annotations

import sqlite3
from typing import Optional

# ---------------------------------------------------------------------------
# Permission sets per role
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


class AuthError(Exception):
    """Raised when a request cannot be authenticated or authorised."""

    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------

# The permissions query is the hottest path in the service (list_reports calls
# it on every request).  We do a single three-table join so the DB can satisfy
# it with the composite index on users(tenant_id, role) together with the
# primary-key lookup on sessions(token).

_RESOLVE_SQL = """
    SELECT
        u.id          AS user_id,
        u.tenant_id   AS tenant_id,
        u.role        AS role,
        t.suspended   AS tenant_suspended
    FROM sessions s
    JOIN users   u ON u.id        = s.user_id
    JOIN tenants t ON t.id        = u.tenant_id
    WHERE s.token      = ?
      AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
"""


def resolve_caller(conn: sqlite3.Connection, request: dict) -> dict:
    """
    Extract the bearer token from *request*, validate it, and return a caller
    dict with keys: ``user_id``, ``tenant_id``, ``role``, ``permissions``.

    Raises :class:`AuthError` (401) if the token is missing or invalid.
    Raises :class:`AuthError` (403) if the tenant is suspended.
    """
    token = _extract_token(request)
    row = conn.execute(_RESOLVE_SQL, (token,)).fetchone()
    if row is None:
        raise AuthError("Invalid or expired token.", status=401)
    if row["tenant_suspended"]:
        raise AuthError("Tenant is suspended.", status=403)
    return {
        "user_id":     row["user_id"],
        "tenant_id":   row["tenant_id"],
        "role":        row["role"],
        "permissions": _ROLE_PERMISSIONS.get(row["role"], frozenset()),
    }


def require_permission(caller: dict, permission: str) -> None:
    """Raise :class:`AuthError` (403) if *caller* lacks *permission*."""
    if permission not in caller["permissions"]:
        raise AuthError(
            f"Permission '{permission}' required.",
            status=403,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_token(request: dict) -> str:
    """Pull the bearer token out of the Authorization header."""
    auth_header: Optional[str] = (request.get("headers") or {}).get("Authorization", "")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    # Also accept a top-level token key (convenience for tests / internal calls).
    token = request.get("token", "")
    if token:
        return token
    raise AuthError("Authorization header missing or malformed.", status=401)
