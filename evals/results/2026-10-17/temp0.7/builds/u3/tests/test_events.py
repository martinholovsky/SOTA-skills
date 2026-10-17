"""Tests for the event dispatcher."""
import pytest
from reportkit import events


@pytest.fixture(autouse=True)
def clean_registry():
    events.clear()
    yield
    events.clear()


def test_dispatch_calls_handler():
    received = []
    events.register("test.event", lambda p: received.append(p))
    events.dispatch("test.event", {"key": "value"})
    assert received == [{"key": "value"}]


def test_dispatch_multiple_handlers():
    log = []
    events.register("x", lambda p: log.append("a"))
    events.register("x", lambda p: log.append("b"))
    events.dispatch("x", {})
    assert log == ["a", "b"]


def test_dispatch_no_handlers_is_safe():
    events.dispatch("no.such.event", {"x": 1})  # must not raise


def test_handler_error_does_not_stop_others():
    log = []
    events.register("y", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
    events.register("y", lambda p: log.append("ran"))
    events.dispatch("y", {})
    assert log == ["ran"]


def test_clear_removes_all():
    events.register("z", lambda p: None)
    events.clear()
    # No handlers remain; dispatch is a no-op
    events.dispatch("z", {})


def test_quota_exceeded_stub_does_not_raise():
    # Re-register the built-in handlers after clear
    from reportkit.events import (
        _on_quota_exceeded,
        register,
        dispatch,
    )
    register("tenant.quota_exceeded", _on_quota_exceeded)
    dispatch("tenant.quota_exceeded", {"tenant_id": "t1"})  # must not raise
