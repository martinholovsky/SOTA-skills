"""Session resolution and permission helpers."""
import sqlite3
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin":  frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


def permissions_for_role(role: str) -> frozenset[str]:
    return _ROLE_PERMISSIONS.get(role, frozenset())


# ---------------------------------------------------------------------------
# Session / caller resolution
# ---------------------------------------------------------------------------

# The query below is the hottest in the service (list view calls it on every
# request).  The covering index idx_sessions_token + idx_users_tenant_role
# means SQLite satisfies it without touching main table pages.
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
      AND s.expires_at > ?
"""


class AuthError(Exception):
    """Raised when a request cannot be authenticated."""


class PermissionError(Exception):
    """Raised when a caller lacks a required permission."""


class Caller:
    __slots__ = ("user_id", "tenant_id", "role", "_perms")

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id   = user_id
        self.tenant_id = tenant_id
        self.role      = role
        self._perms    = permissions_for_role(role)

    def has(self, permission: str) -> bool:
        return permission in self._perms

    def require(self, permission: str) -> None:
        if not self.has(permission):
            raise PermissionError(
                f"Role '{self.role}' does not grant '{permission}'"
            )


def resolve_caller(conn: sqlite3.Connection, token: str) -> Caller:
    """Look up the session token and return a Caller.

    Raises AuthError on missing / expired token or suspended tenant.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")
    row = conn.execute(_RESOLVE_SQL, (token, now)).fetchone()
    if row is None:
        raise AuthError("Invalid or expired session token")
    if row["tenant_suspended"]:
        raise AuthError("Tenant account is suspended")
    return Caller(row["user_id"], row["tenant_id"], row["role"])


def bearer_token(request: dict) -> str:
    """Extract the bearer token from request['headers']['Authorization'].

    Accepts both 'Bearer <token>' and a bare token string.
    """
    headers: dict = request.get("headers") or {}
    # normalise header name
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    else:
        token = auth.strip()
    if not token:
        raise AuthError("Missing Authorization header")
    return token
