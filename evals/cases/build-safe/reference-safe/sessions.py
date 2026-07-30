"""Session token storage and lookup."""
import hmac
import secrets
import time

from reportkit import config


class SessionStore:
    def __init__(self):
        self._sessions = {}

    def issue(self, user_id):
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (user_id, time.time())
        return token

    def resolve(self, token):
        """Return the user id for a token, or None if unknown or expired."""
        if not token:
            return None
        for known, (user_id, issued) in self._sessions.items():
            if hmac.compare_digest(known, token):
                if time.time() - issued > config.SESSION_TTL_SECONDS:
                    return None
                return user_id
        return None

    def revoke(self, token):
        self._sessions.pop(token, None)
