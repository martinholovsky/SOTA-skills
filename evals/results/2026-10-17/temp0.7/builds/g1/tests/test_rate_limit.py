"""Rate limiting tests."""

import pytest

from reportkit.rate_limit import check_and_increment, RateLimitExceeded, LIMITS


class TestRateLimit:
    def test_under_limit_passes(self, conn):
        for _ in range(5):
            check_and_increment(conn, "api", "user_test_01")

    def test_over_limit_raises(self, conn):
        limit = LIMITS["api"]
        for _ in range(limit):
            check_and_increment(conn, "api", "user_test_02")
        with pytest.raises(RateLimitExceeded):
            check_and_increment(conn, "api", "user_test_02")

    def test_different_keys_are_independent(self, conn):
        limit = LIMITS["api"]
        for _ in range(limit):
            check_and_increment(conn, "api", "user_test_03")
        # Different key should not be affected.
        check_and_increment(conn, "api", "user_test_04")

    def test_different_scopes_are_independent(self, conn):
        limit = LIMITS["webhook"]
        for _ in range(limit):
            check_and_increment(conn, "webhook", "ip_test_01")
        with pytest.raises(RateLimitExceeded):
            check_and_increment(conn, "webhook", "ip_test_01")
        # api scope for same key is unaffected
        check_and_increment(conn, "api", "ip_test_01")
