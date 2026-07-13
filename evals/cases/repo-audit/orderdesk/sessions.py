"""Server-side session store.

Sessions are opaque tokens mapped to a user id. Call `revoke_all_for_user`
whenever a user's credentials change so that outstanding sessions cannot be
replayed after a password reset or account takeover recovery.
"""
from .db import Database
from .tokens import make_token


class SessionStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, user_id: int) -> str:
        token = make_token(48)
        self._db.execute(
            "INSERT INTO sessions (token, user_id) VALUES (%s, %s)",
            (token, user_id),
        )
        return token

    def user_for(self, token: str) -> int | None:
        rows = self._db.query(
            "SELECT user_id FROM sessions WHERE token = %s", (token,)
        )
        return rows[0]["user_id"] if rows else None

    def revoke(self, token: str) -> None:
        self._db.execute("DELETE FROM sessions WHERE token = %s", (token,))

    def revoke_all_for_user(self, user_id: int) -> None:
        """Invalidate every session for a user (use on credential change)."""
        self._db.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
