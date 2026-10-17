"""Event dispatcher tests."""

from __future__ import annotations

import pytest

import reportkit.events as ev


def test_dispatch_calls_handler():
    received = []
    ev.register("test.event", lambda p: received.append(p))
    ev.dispatch("test.event", {"key": "value"})
    assert received == [{"key": "value"}]


def test_dispatch_unknown_event_is_noop():
    # Should not raise
    ev.dispatch("no.such.event", {})


def test_handler_exception_does_not_abort_others():
    results = []

    def bad_handler(p):
        raise RuntimeError("boom")

    def good_handler(p):
        results.append(p)

    ev.register("test.resilience", bad_handler)
    ev.register("test.resilience", good_handler)
    ev.dispatch("test.resilience", {"x": 1})
    assert results == [{"x": 1}]


def test_quota_exceeded_stub_registered():
    """The tenant.quota_exceeded stub must be registered (not silently absent)."""
    handlers = ev._registry.get("tenant.quota_exceeded", [])
    assert len(handlers) >= 1
