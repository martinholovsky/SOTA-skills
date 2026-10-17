"""Rate limiter tests."""

from __future__ import annotations

import pytest

from reportkit.errors import RateLimited
from reportkit.rate_limit import _Bucket, check


def test_bucket_allows_within_capacity():
    b = _Bucket(capacity=5, refill_rate=1.0)
    for _ in range(5):
        assert b.consume() is True


def test_bucket_denies_when_exhausted():
    b = _Bucket(capacity=2, refill_rate=0.0)  # no refill
    b.consume()
    b.consume()
    assert b.consume() is False


def test_check_raises_when_exhausted(monkeypatch):
    import reportkit.rate_limit as rl

    # Replace buckets with a fresh dict for isolation
    monkeypatch.setattr(rl, "_buckets", {})
    monkeypatch.setitem(rl._ENDPOINT_LIMITS, "_test_ep", (2, 0.0))

    check("user1", "_test_ep")
    check("user1", "_test_ep")
    with pytest.raises(RateLimited):
        check("user1", "_test_ep")


def test_different_callers_independent(monkeypatch):
    import reportkit.rate_limit as rl

    monkeypatch.setattr(rl, "_buckets", {})
    monkeypatch.setitem(rl._ENDPOINT_LIMITS, "_test_ep2", (1, 0.0))

    check("userA", "_test_ep2")
    # userA exhausted; userB still has capacity
    check("userB", "_test_ep2")
    with pytest.raises(RateLimited):
        check("userA", "_test_ep2")
