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
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------

def resolve_session(conn: sqlite3.Connection, token: str) -> sqlite3.Row:
    """
    Return the user row for *token*.

    The query joins sessions → users → tenants so that the caller's role and
    tenant suspension status are available in a single round-trip.  This is
    the hot path for every authenticated request.
    """
    row = conn.execute(
        """
        SELECT
            u.id          AS user_id,
            u.tenant_id,
            u.username,
            u.role,
            t.suspended   AS tenant_suspended
        FROM sessions s
        JOIN users   u ON u.id = s.user_id
        JOIN tenants t ON t.id = u.tenant_id
        WHERE s.token = ?
          AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        (token,),
    ).fetchone()

    if row is None:
        raise AuthError("Invalid or expired token", status=401)

    if row["tenant_suspended"]:
        raise AuthError("Tenant is suspended", status=403)

    return row


def extract_token(request: dict) -> str:
    """Pull the bearer token out of *request['headers']['Authorization']*."""
    auth_header: str = (request.get("headers") or {}).get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise AuthError("Missing or malformed Authorization header", status=401)
    token = auth_header[7:].strip()
    if not token:
        raise AuthError("Empty bearer token", status=401)
    return token


def authenticate(conn: sqlite3.Connection, request: dict) -> sqlite3.Row:
    """Convenience: extract token then resolve session."""
    token = extract_token(request)
    return resolve_session(conn, token)


def require_permission(user_row: sqlite3.Row, permission: str) -> None:
    """Raise *AuthError(403)* if the user lacks *permission*."""
    role = user_row["role"]
    perms = _ROLE_PERMISSIONS.get(role, frozenset())
    if permission not in perms:
        raise AuthError(
            f"Role '{role}' does not grant '{permission}'",
            status=403,
        )


def permissions_for_role(role: str) -> frozenset[str]:
    return _ROLE_PERMISSIONS.get(role, frozenset())
