"""Tests for the event registry."""

import pytest
from reportkit import events as ev


@pytest.fixture(autouse=True)
def clean_registry():
    """Isolate each test by saving and restoring the registry."""
    original = dict(ev._registry)
    yield
    ev._registry.clear()
    ev._registry.update(original)


class TestRegisterAndDispatch:
    def test_handler_is_called(self):
        received = []
        ev.register("test.event", lambda p: received.append(p))
        ev.dispatch("test.event", {"x": 1})
        assert received == [{"x": 1}]

    def test_multiple_handlers_all_called(self):
        log = []
        ev.register("multi", lambda p: log.append("a"))
        ev.register("multi", lambda p: log.append("b"))
        ev.dispatch("multi", {})
        assert log == ["a", "b"]

    def test_no_handlers_is_silent(self):
        ev.dispatch("no.handlers", {})  # no exception

    def test_failing_handler_does_not_block_others(self):
        log = []

        def bad(p):
            raise RuntimeError("boom")

        ev.register("err.event", bad)
        ev.register("err.event", lambda p: log.append("ok"))

        with pytest.raises(ExceptionGroup):
            ev.dispatch("err.event", {})

        assert "ok" in log

    def test_exception_group_raised_on_error(self):
        ev.register("fail", lambda p: (_ for _ in ()).throw(ValueError("oops")))
        with pytest.raises(ExceptionGroup) as exc_info:
            ev.dispatch("fail", {})
        assert len(exc_info.value.exceptions) == 1
