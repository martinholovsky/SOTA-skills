"""Event dispatcher and quota-exceeded placeholder tests."""

import pytest

from reportkit import events


def test_dispatch_calls_handler():
    received = []

    def handler(payload):
        received.append(payload)

    # Use a unique event name to avoid polluting the shared registry
    events.register("test.event_dispatch", handler)
    events.dispatch("test.event_dispatch", {"key": "value"})
    assert received == [{"key": "value"}]


def test_dispatch_no_handler_is_silent():
    # Should not raise
    events.dispatch("test.no_such_event_xyz", {})


def test_handler_exception_does_not_propagate():
    def bad_handler(payload):
        raise RuntimeError("boom")

    events.register("test.bad_handler", bad_handler)
    # Must not raise
    events.dispatch("test.bad_handler", {})


def test_quota_exceeded_placeholder_does_not_raise():
    # The placeholder handler is registered at import time
    events.dispatch("tenant.quota_exceeded", {"tenant_id": "t1"})
