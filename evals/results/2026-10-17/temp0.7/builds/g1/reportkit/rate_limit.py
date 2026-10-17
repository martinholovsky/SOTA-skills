"""
Token-bucket rate limiting backed by SQLite.

Keyed on (scope, key) where key is typically a user_id or IP address.
Uses a fixed-window counter per minute stored in the DB.

For the billing webhook we key on "webhook" scope with the remote IP.
For API calls we key on "api" scope with the user_id.

This is the application-level control.  The spec notes that a gateway
may provide additional rate limiting; if so, note it in NOTES.md.
"""

import logging
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Limits per minute per key.
LIMITS: dict[str, int] = {
    "api":     120,   # per authenticated user
    "webhook": 60,    # per source IP for billing webhooks
}


class RateLimitExceeded(Exception):
    """Raised when the caller exceeds the configured rate limit."""
    def __init__(self, scope: str):
        self.scope = scope
        super().__init__(f"rate limit exceeded for scope '{scope}'")


def check_and_increment(
    conn: sqlite3.Connection,
    scope: str,
    key: str,
) -> None:
    """
    Increment the counter for (scope, key) in the current minute window.
    Raises RateLimitExceeded if the limit is exceeded.

    Uses an upsert so the check and increment are atomic within SQLite's
    serialized write model.
    """
    limit = LIMITS.get(scope, 60)
    window = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

    conn.execute(
        """
        INSERT INTO rate_limit_buckets (scope, key, window_start, count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT (scope, key, window_start)
        DO UPDATE SET count = count + 1
        """,
        (scope, key, window),
    )

    row = conn.execute(
        "SELECT count FROM rate_limit_buckets WHERE scope=? AND key=? AND window_start=?",
        (scope, key, window),
    ).fetchone()

    if row and row["count"] > limit:
        logger.warning(
            "rate_limit_exceeded scope=%s key_prefix=%s window=%s count=%d limit=%d",
            scope,
            # Log only first 8 chars of key to avoid full user_id in logs.
            key[:8] + "…",
            window,
            row["count"],
            limit,
        )
        raise RateLimitExceeded(scope)
