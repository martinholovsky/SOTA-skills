"""Password-reset flow: request a reset, then set a new password by token."""
import hashlib
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import get_db, hash_password
from .db import Database
from .ratelimit import limiter
from .tokens import make_token

router = APIRouter(prefix="/reset", tags=["reset"])
_TTL_SECONDS = 900


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    new_password: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/request")
def request_reset(data: ResetRequest, db: Database = Depends(get_db)) -> dict:
    limiter.check(f"reset:req:{data.email}")
    rows = db.query("SELECT id FROM users WHERE email = %s", (data.email,))
    if rows:
        token = make_token(32)
        db.execute(
            "INSERT INTO reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (rows[0]["id"], _hash_token(token), time.time() + _TTL_SECONDS),
        )
        _send_email(data.email, token)
    # Uniform response regardless of whether the email exists (no enumeration).
    return {"status": "if the address exists, a reset link was sent"}


@router.post("/confirm")
def confirm_reset(data: ResetConfirm, db: Database = Depends(get_db)) -> dict:
    limiter.check("reset:confirm")
    rows = db.query(
        "SELECT user_id, expires_at FROM reset_tokens WHERE token_hash = %s",
        (_hash_token(data.token),),
    )
    if not rows or rows[0]["expires_at"] < time.time():
        return {"status": "invalid or expired"}
    db.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_password(data.new_password), rows[0]["user_id"]),
    )
    db.execute("DELETE FROM reset_tokens WHERE token_hash = %s", (_hash_token(data.token),))
    return {"status": "ok"}


def _send_email(to: str, token: str) -> None:  # pragma: no cover - fixture stub
    pass
