"""Rate limiter unit tests."""

import pytest

from reportkit.rate_limit import RateLimiter


def test_allows_within_burst():
    rl = RateLimiter(burst_capacity=5, burst_period_s=1.0,
                     sustain_capacity=100, sustain_period_s=60.0)
    for _ in range(5):
        assert rl.check("t1", "u1") is True


def test_blocks_over_burst():
    rl = RateLimiter(burst_capacity=3, burst_period_s=10.0,
                     sustain_capacity=100, sustain_period_s=60.0)
    for _ in range(3):
        rl.check("t1", "u1")
    assert rl.check("t1", "u1") is False


def test_different_users_independent():
    rl = RateLimiter(burst_capacity=2, burst_period_s=10.0,
                     sustain_capacity=100, sustain_period_s=60.0)
    for _ in range(2):
        rl.check("t1", "u1")
    # u1 is exhausted; u2 should still be allowed
    assert rl.check("t1", "u2") is True


def test_different_tenants_independent():
    rl = RateLimiter(burst_capacity=2, burst_period_s=10.0,
                     sustain_capacity=100, sustain_period_s=60.0)
    for _ in range(2):
        rl.check("t1", "u1")
    assert rl.check("t2", "u1") is True


def test_sustain_limit():
    rl = RateLimiter(burst_capacity=1000, burst_period_s=0.001,
                     sustain_capacity=3, sustain_period_s=3600.0)
    for _ in range(3):
        assert rl.check("t1", "u1") is True
    assert rl.check("t1", "u1") is False
