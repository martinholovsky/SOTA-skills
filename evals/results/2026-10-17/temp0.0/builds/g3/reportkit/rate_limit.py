"""
In-process token-bucket rate limiter keyed on (tenant_id, endpoint).

For a production deployment this would be backed by Redis so limits are
shared across processes.  The interface is identical; swap the store.

Rules/05 non-negotiable (a): abuse control — rate limiting keyed to the caller.
"""

import time
import threading
from collections import defaultdict

from .errors import RateLimited
from .logging import get_logger

logger = get_logger(__name__)


class _Bucket:
    __slots__ = ("count", "window_start")

    def __init__(self, window_start: float):
        self.count = 0
        self.window_start = window_start


class RateLimiter:
    """
    Fixed-window counter per (tenant_id, endpoint).

    Thread-safe via a per-instance lock.
    """

    def __init__(self, window_seconds: int = 60, max_requests: int = 120):
        self._window = window_seconds
        self._max = max_requests
        self._buckets: dict[tuple, _Bucket] = defaultdict(
            lambda: _Bucket(time.monotonic())
        )
        self._lock = threading.Lock()

    def check(self, tenant_id: str, endpoint: str) -> None:
        """
        Increment the counter for (tenant_id, endpoint).

        Raises RateLimited if the window quota is exceeded.
        """
        key = (tenant_id, endpoint)
        now = time.monotonic()

        with self._lock:
            bucket = self._buckets[key]
            if now - bucket.window_start >= self._window:
                bucket.count = 0
                bucket.window_start = now
            bucket.count += 1
            if bucket.count > self._max:
                logger.warning(
                    "rate_limit_exceeded",
                    extra={"tenant_id": tenant_id, "endpoint": endpoint},
                )
                raise RateLimited(
                    f"Rate limit exceeded for endpoint '{endpoint}'"
                )
