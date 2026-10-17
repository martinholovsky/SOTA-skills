"""In-process token-bucket rate limiter.

Keyed by (caller_id, endpoint).  Designed to be replaced by a Redis-backed
implementation at the gateway layer; this provides a defence-in-depth floor
when the service is called directly (e.g. in tests or internal tooling).

NOTE: because this is in-process, limits are per-worker-process.  A
production deployment behind a gateway should enforce limits there and treat
this as a secondary control.  See NOTES.md.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from reportkit.errors import RateLimited


@dataclass
class _Bucket:
    capacity: float
    refill_rate: float          # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.last_refill = time.monotonic()

    def consume(self, cost: float = 1.0) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False


# Default limits per endpoint (capacity, refill_rate tokens/sec)
_ENDPOINT_LIMITS: dict[str, tuple[float, float]] = {
    "create_report":      (20,  1.0),
    "get_report":         (60,  5.0),
    "list_reports":       (60,  5.0),
    "search_reports":     (30,  2.0),
    "delete_report":      (20,  1.0),
    "upload_attachment":  (10,  0.5),
    "billing_webhook":    (60,  5.0),
    "default":            (30,  2.0),
}

_buckets: dict[tuple[str, str], _Bucket] = {}
_buckets_lock = threading.Lock()


def _get_bucket(caller_id: str, endpoint: str) -> _Bucket:
    key = (caller_id, endpoint)
    with _buckets_lock:
        if key not in _buckets:
            cap, rate = _ENDPOINT_LIMITS.get(endpoint, _ENDPOINT_LIMITS["default"])
            _buckets[key] = _Bucket(capacity=cap, refill_rate=rate)
        return _buckets[key]


def check(caller_id: str, endpoint: str) -> None:
    """Raise RateLimited if the caller has exhausted their quota for *endpoint*."""
    bucket = _get_bucket(caller_id, endpoint)
    if not bucket.consume():
        raise RateLimited(f"rate limit exceeded for {endpoint}")
