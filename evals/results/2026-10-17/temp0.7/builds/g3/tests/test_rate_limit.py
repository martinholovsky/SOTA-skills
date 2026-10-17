"""Tests for the rate limiter."""

import time
import pytest
from reportkit.rate_limit import check_rate_limit, RateLimitExceeded


def test_within_limit_passes(conn):
    for _ in range(60):
        check_rate_limit(conn, "user1", "get_report", now=1_000_000.0)


def test_exceeds_limit_raises(conn):
    with pytest.raises(RateLimitExceeded):
        for _ in range(130):   # limit is 120
            check_rate_limit(conn, "user2", "get_report", now=1_000_000.0)


def test_new_window_resets_counter(conn):
    for _ in range(120):
        check_rate_limit(conn, "user3", "get_report", now=1_000_000.0)
    # Move to the next 60-second window.
    for _ in range(120):
        check_rate_limit(conn, "user3", "get_report", now=1_000_060.0)


def test_different_callers_independent(conn):
    for _ in range(120):
        check_rate_limit(conn, "userA", "get_report", now=2_000_000.0)
    # userB is unaffected.
    check_rate_limit(conn, "userB", "get_report", now=2_000_000.0)


def test_different_endpoints_independent(conn):
    for _ in range(60):
        check_rate_limit(conn, "user4", "create_report", now=3_000_000.0)
    # A different endpoint has its own counter.
    check_rate_limit(conn, "user4", "get_report", now=3_000_000.0)
