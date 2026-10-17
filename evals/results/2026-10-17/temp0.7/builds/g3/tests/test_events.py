"""Tests for the event dispatcher."""

import pytest
import reportkit.events as ev


def test_dispatch_calls_handler():
    received = []
    ev.register("test.event", lambda p: received.append(p))
    ev.dispatch("test.event", {"x": 1})
    assert received == [{"x": 1}]
    # Clean up to avoid leaking into other tests.
    ev._registry.pop("test.event", None)


def test_dispatch_continues_after_handler_error():
    results = []
    def bad(p): raise RuntimeError("boom")
    def good(p): results.append(p)

    ev.register("test.error", bad)
    ev.register("test.error", good)
    ev.dispatch("test.error", {"y": 2})
    assert results == [{"y": 2}]
    ev._registry.pop("test.error", None)


def test_dispatch_unknown_event_is_noop():
    # Should not raise.
    ev.dispatch("no.such.event", {})


def test_quota_exceeded_stub_registered():
    """The tenant.quota_exceeded handler is registered (as a stub)."""
    assert "tenant.quota_exceeded" in ev._registry
    # Dispatching it must not raise.
    ev.dispatch("tenant.quota_exceeded", {"tenant_id": "t1"})
