"""Tests for the event registry."""

import pytest

from reportkit.events import EventRegistry


class TestEventRegistry:
    def test_handler_called(self):
        reg = EventRegistry()
        received = []
        reg.register("foo", lambda p: received.append(p))
        reg.dispatch("foo", {"x": 1})
        assert received == [{"x": 1}]

    def test_multiple_handlers(self):
        reg = EventRegistry()
        log = []
        reg.register("evt", lambda p: log.append("a"))
        reg.register("evt", lambda p: log.append("b"))
        reg.dispatch("evt", {})
        assert log == ["a", "b"]

    def test_unknown_event_no_error(self):
        reg = EventRegistry()
        reg.dispatch("no.such.event", {})  # should not raise

    def test_failing_handler_does_not_block_others(self):
        reg = EventRegistry()
        log = []
        reg.register("evt", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
        reg.register("evt", lambda p: log.append("ran"))
        reg.dispatch("evt", {})
        assert log == ["ran"]

    def test_decorator_registration(self):
        reg = EventRegistry()
        received = []

        @reg.handler("my.event")
        def h(payload):
            received.append(payload)

        reg.dispatch("my.event", {"k": "v"})
        assert received == [{"k": "v"}]
