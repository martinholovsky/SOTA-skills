"""Authentication: password hashing and the request-user dependency."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException

from .db import Database
from .sessions import SessionStore

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return _ph.verify(stored_hash, plain)
    except VerifyMismatchError:
        return False


class User:
    def __init__(self, user_id: int, is_admin: bool = False) -> None:
        self.id = user_id
        self.is_admin = is_admin


def get_db() -> Database:  # overridden in app wiring / tests
    raise NotImplementedError


def require_user(
    authorization: str = Header(default=""),
    db: Database = Depends(get_db),
) -> User:
    """Resolve the caller from their session token or reject with 401."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    user_id = SessionStore(db).user_for(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    rows = db.query("SELECT id, is_admin FROM users WHERE id = %s", (user_id,))
    if not rows:
        raise HTTPException(status_code=401, detail="authentication required")
    return User(rows[0]["id"], bool(rows[0]["is_admin"]))
