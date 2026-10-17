"""Event dispatcher tests."""

import pytest

from reportkit.events import (
    register,
    dispatch,
    clear_all_handlers,
    EVENT_REPORT_CREATED,
    EVENT_REPORT_DELETED,
    EVENT_QUOTA_EXCEEDED,
)


@pytest.fixture(autouse=True)
def reset():
    clear_all_handlers()
    yield
    clear_all_handlers()


class TestEventDispatcher:
    def test_registered_handler_called(self):
        received = []
        register(EVENT_REPORT_CREATED, lambda p: received.append(p))
        dispatch(EVENT_REPORT_CREATED, {"report_id": "x"})
        assert received == [{"report_id": "x"}]

    def test_no_handlers_no_error(self):
        dispatch(EVENT_REPORT_CREATED, {"report_id": "x"})

    def test_multiple_handlers_all_called(self):
        log = []
        register(EVENT_REPORT_DELETED, lambda p: log.append("h1"))
        register(EVENT_REPORT_DELETED, lambda p: log.append("h2"))
        dispatch(EVENT_REPORT_DELETED, {})
        assert log == ["h1", "h2"]

    def test_failing_handler_does_not_abort_others(self):
        log = []
        register(EVENT_REPORT_CREATED, lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
        register(EVENT_REPORT_CREATED, lambda p: log.append("ok"))
        dispatch(EVENT_REPORT_CREATED, {})
        assert log == ["ok"]

    def test_quota_exceeded_event_registered_but_no_handler(self):
        # Verifies the event name constant exists and dispatching it is safe
        # (no handler wired in; the batch-import feed is retired).
        dispatch(EVENT_QUOTA_EXCEEDED, {"tenant_id": "t"})

    def test_unknown_event_is_safe(self):
        dispatch("unknown.event", {})
