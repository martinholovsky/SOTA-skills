"""A minimal fixed-window rate limiter, keyed by caller identity."""
import time

from fastapi import HTTPException

from .config import settings


class RateLimiter:
    def __init__(self, per_minute: int | None = None) -> None:
        self._limit = per_minute or settings.rate_limit_per_minute
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        window = self._hits.setdefault(key, [])
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= self._limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        window.append(now)


limiter = RateLimiter()
