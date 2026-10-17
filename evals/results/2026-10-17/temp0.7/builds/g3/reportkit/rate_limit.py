"""
Simple token-bucket / fixed-window rate limiter backed by SQLite.

Keyed by (caller_id, endpoint).  The window is 60 seconds; limits are
configurable per endpoint.

This is the application-layer rate limiter.  A gateway-level limiter is
expected in production (see NOTES.md); this layer defends the service
when requests reach it directly (e.g. internal callers, tests).
"""

import time
from typing import Optional


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds the per-window limit."""
    def __init__(self, limit: int, window_seconds: int):
        super().__init__(
            f"rate limit exceeded: {limit} requests per {window_seconds}s"
        )
        self.status = 429
        self.limit  = limit
        self.window = window_seconds


# Default limits: (max_requests, window_seconds)
_ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
    "create_report":    (60,  60),
    "get_report":       (120, 60),
    "list_reports":     (120, 60),
    "search_reports":   (60,  60),
    "delete_report":    (30,  60),
    "upload_attachment":(20,  60),
    "billing_webhook":  (30,  60),
}
_DEFAULT_LIMIT = (60, 60)


def check_rate_limit(
    conn,
    caller_id: str,
    endpoint: str,
    *,
    now: Optional[float] = None,
) -> None:
    """
    Increment the counter for (caller_id, endpoint) in the current window.

    Raises RateLimitExceeded if the caller has exceeded the limit.
    Cleans up expired windows lazily.
    """
    max_req, window_sec = _ENDPOINT_LIMITS.get(endpoint, _DEFAULT_LIMIT)
    ts = now if now is not None else time.time()
    # Truncate to the start of the current window.
    window_start = str(int(ts // window_sec) * window_sec)
    bucket_key   = f"{caller_id}:{endpoint}"

    # Lazy cleanup: delete windows older than 2× the window size.
    cutoff = str(int(ts // window_sec - 1) * window_sec)
    conn.execute(
        "DELETE FROM rate_limit_counters WHERE bucket_key = ? AND window_start < ?",
        (bucket_key, cutoff),
    )

    conn.execute(
        """
        INSERT INTO rate_limit_counters (bucket_key, window_start, count)
             VALUES (?, ?, 1)
        ON CONFLICT (bucket_key, window_start)
        DO UPDATE SET count = count + 1
        """,
        (bucket_key, window_start),
    )

    row = conn.execute(
        "SELECT count FROM rate_limit_counters WHERE bucket_key = ? AND window_start = ?",
        (bucket_key, window_start),
    ).fetchone()

    if row and row["count"] > max_req:
        raise RateLimitExceeded(max_req, window_sec)
