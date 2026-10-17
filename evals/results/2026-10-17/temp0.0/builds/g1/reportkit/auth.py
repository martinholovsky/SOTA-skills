"""Authentication — bearer-token resolution and permission checks.

The bearer token is hashed (SHA-256) before any DB lookup so the raw secret
never touches the database.  Permissions are derived from the role at
request time (no stale session cache for role data).
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import TypedDict

from reportkit.errors import Forbidden, TenantSuspended, Unauthorized

# ---------------------------------------------------------------------------
# Permission model
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"report:read"}),
    "editor": frozenset({"report:read", "report:write"}),
    "admin": frozenset({"report:read", "report:write", "report:delete", "user:manage"}),
}


class Principal(TypedDict):
    user_id: str
    tenant_id: str
    role: str
    permissions: frozenset[str]


# ---------------------------------------------------------------------------
# Token hashing
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """Return the hex SHA-256 digest of *token*."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------


def resolve_principal(conn: sqlite3.Connection, request: dict) -> Principal:
    """Resolve the bearer token in *request* to a Principal.

    Raises Unauthorized if the token is missing, expired, or unknown.
    Raises TenantSuspended if the tenant is suspended.

    Role is re-read from the DB on every call so that ops-console role changes
    take effect immediately without requiring a new session.
    """
    auth_header: str = request.get("headers", {}).get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise Unauthorized("missing or malformed Authorization header")

    raw_token = auth_header[len("Bearer "):]
    if not raw_token:
        raise Unauthorized("empty bearer token")

    token_hash = _hash_token(raw_token)

    # Single query: join session → user → tenant so we get everything atomically
    # and re-read the current role (not a cached snapshot).
    row = conn.execute(
        """
        SELECT
            u.id          AS user_id,
            u.tenant_id   AS tenant_id,
            u.role        AS role,
            t.suspended   AS suspended
        FROM sessions s
        JOIN users   u ON u.id = s.user_id
        JOIN tenants t ON t.id = u.tenant_id
        WHERE s.token_hash = ?
          AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        (token_hash,),
    ).fetchone()

    if row is None:
        raise Unauthorized("invalid or expired session token")

    if row["suspended"]:
        raise TenantSuspended("tenant is suspended")

    role: str = row["role"]
    permissions = _ROLE_PERMISSIONS.get(role, frozenset())

    return Principal(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        role=role,
        permissions=permissions,
    )


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------


def require_permission(principal: Principal, permission: str) -> None:
    """Raise Forbidden if *principal* lacks *permission*."""
    if permission not in principal["permissions"]:
        raise Forbidden(f"permission required: {permission}")
