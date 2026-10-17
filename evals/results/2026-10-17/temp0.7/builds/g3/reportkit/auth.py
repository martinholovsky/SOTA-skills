"""
Authentication helpers.

Bearer tokens are resolved to a (user_id, tenant_id, role) triple by
looking up SHA-256(token) in the sessions table.  The raw token is never
stored.

Permissions are derived purely from role; no DB round-trip is needed for
the permission check itself.
"""

import hashlib
import hmac
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
    return _ROLE_PERMISSIONS.get(role, frozenset())


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------

def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AuthError(Exception):
    """Raised when a token is missing, expired, or invalid."""
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


class Principal:
    """Resolved identity attached to a request."""
    __slots__ = ("user_id", "tenant_id", "role", "permissions")

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id   = user_id
        self.tenant_id = tenant_id
        self.role      = role
        self.permissions: frozenset[str] = permissions_for_role(role)

    def require(self, permission: str) -> None:
        """Raise AuthError(403) if the permission is absent."""
        if permission not in self.permissions:
            raise AuthError(
                f"permission '{permission}' required",
                status=403,
            )

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def resolve_principal(request: dict, conn) -> Principal:
    """
    Extract and validate the bearer token from *request*, returning a
    Principal.

    The caller must pass the open DB connection so this function can be
    called from inside a transaction.

    Raises AuthError on any failure.
    """
    auth_header: Optional[str] = (
        request.get("headers", {}).get("Authorization")
        or request.get("headers", {}).get("authorization")
    )
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("missing or malformed Authorization header", status=401)

    raw_token = auth_header[len("Bearer "):]
    if not raw_token:
        raise AuthError("empty bearer token", status=401)

    token_hash = _hash_token(raw_token)

    row = conn.execute(
        """
        SELECT s.user_id, u.tenant_id, u.role
          FROM sessions s
          JOIN users    u ON u.id = s.user_id
          JOIN tenants  t ON t.id = u.tenant_id
         WHERE s.token_hash = ?
           AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
           AND t.suspended  = 0
        """,
        (token_hash,),
    ).fetchone()

    if row is None:
        raise AuthError("invalid or expired token", status=401)

    return Principal(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        role=row["role"],
    )


# ---------------------------------------------------------------------------
# HMAC verification (used by the billing webhook)
# ---------------------------------------------------------------------------

def verify_hmac_sha256(secret: bytes, body: bytes, provided_hex: str) -> bool:
    """
    Constant-time HMAC-SHA256 comparison.

    Returns True iff HMAC(secret, body) == provided_hex.
    """
    expected = hmac.new(secret, body, "sha256").hexdigest()
    return hmac.compare_digest(expected, provided_hex)
