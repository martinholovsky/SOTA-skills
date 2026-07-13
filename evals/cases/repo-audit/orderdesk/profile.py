"""Self-service profile routes."""
from fastapi import APIRouter, Depends, HTTPException

from .auth import User, get_db, hash_password, require_user, verify_password
from .db import Database
from .models import PasswordChange
from .ratelimit import limiter

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    user: User = Depends(require_user),
    db: Database = Depends(get_db),
) -> dict:
    limiter.check(f"profile:pw:{user.id}")
    rows = db.query("SELECT password_hash FROM users WHERE id = %s", (user.id,))
    if not rows or not verify_password(rows[0]["password_hash"], data.current_password):
        raise HTTPException(status_code=400, detail="invalid credentials")
    db.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_password(data.new_password), user.id),
    )
    return {"status": "ok"}
