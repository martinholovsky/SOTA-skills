"""
In-process token-bucket rate limiter.

Rules applied
-------------
- Non-negotiable §a: rate limiting keyed to the caller.
- Two windows per caller: burst (10 req / 1 s) and sustained (200 req / 60 s).
- Keyed on (tenant_id, user_id) so one noisy user cannot starve another
  tenant's quota.
- Thread-safe via a per-key lock.

Production note: in a multi-process or multi-host deployment this must be
replaced with a shared store (Redis INCR + EXPIRE or a sliding-window
counter).  The interface is identical so the swap is a one-liner.
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)


class RateLimiter:
    """
    Token-bucket limiter with two independent windows.

    burst_capacity  / burst_period_s  — short burst allowance
    sustain_capacity / sustain_period_s — sustained rate
    """

    def __init__(
        self,
        burst_capacity: int = 10,
        burst_period_s: float = 1.0,
        sustain_capacity: int = 200,
        sustain_period_s: float = 60.0,
    ):
        self._burst_cap    = burst_capacity
        self._burst_rate   = burst_capacity / burst_period_s
        self._sustain_cap  = sustain_capacity
        self._sustain_rate = sustain_capacity / sustain_period_s
        self._buckets: dict[str, tuple[_Bucket, _Bucket]] = {}
        self._map_lock = threading.Lock()

    def _get_buckets(self, key: str) -> tuple[_Bucket, _Bucket]:
        with self._map_lock:
            if key not in self._buckets:
                now = time.monotonic()
                burst   = _Bucket(tokens=float(self._burst_cap),   last_refill=now)
                sustain = _Bucket(tokens=float(self._sustain_cap), last_refill=now)
                self._buckets[key] = (burst, sustain)
            return self._buckets[key]

    @staticmethod
    def _consume(bucket: _Bucket, rate: float, capacity: float) -> bool:
        """Refill and attempt to consume 1 token.  Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(capacity, bucket.tokens + elapsed * rate)
        bucket.last_refill = now
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def check(self, tenant_id: str, user_id: str) -> bool:
        """
        Return True if the request is within limits; False if it should be
        rejected with 429.
        """
        key = f"{tenant_id}:{user_id}"
        burst_b, sustain_b = self._get_buckets(key)

        # Both buckets must allow the request
        with burst_b.lock:
            burst_ok = self._consume(burst_b, self._burst_rate, self._burst_cap)
        with sustain_b.lock:
            sustain_ok = self._consume(sustain_b, self._sustain_rate, self._sustain_cap)

        return burst_ok and sustain_ok


# Module-level default instance (replaced in tests)
default_limiter = RateLimiter()
