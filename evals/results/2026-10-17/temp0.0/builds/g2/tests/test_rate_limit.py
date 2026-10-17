"""
Tests for the rate limiter.
"""

import pytest

from reportkit.errors import RateLimited
from reportkit.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_requests_within_limit(self):
        rl = RateLimiter(window_seconds=60, max_requests=5)
        for _ in range(5):
            rl.check("tenant-1", "endpoint")

    def test_blocks_over_limit(self):
        rl = RateLimiter(window_seconds=60, max_requests=3)
        for _ in range(3):
            rl.check("tenant-1", "endpoint")
        with pytest.raises(RateLimited):
            rl.check("tenant-1", "endpoint")

    def test_different_tenants_independent(self):
        rl = RateLimiter(window_seconds=60, max_requests=2)
        rl.check("tenant-1", "ep")
        rl.check("tenant-1", "ep")
        # tenant-2 has its own bucket.
        rl.check("tenant-2", "ep")
        rl.check("tenant-2", "ep")
        with pytest.raises(RateLimited):
            rl.check("tenant-1", "ep")

    def test_different_endpoints_independent(self):
        rl = RateLimiter(window_seconds=60, max_requests=1)
        rl.check("t", "ep1")
        rl.check("t", "ep2")  # different endpoint, own bucket
        with pytest.raises(RateLimited):
            rl.check("t", "ep1")

    def test_window_reset(self):
        import time
        rl = RateLimiter(window_seconds=1, max_requests=1)
        rl.check("t", "ep")
        with pytest.raises(RateLimited):
            rl.check("t", "ep")
        time.sleep(1.05)
        # Window has reset; should succeed again.
        rl.check("t", "ep")
