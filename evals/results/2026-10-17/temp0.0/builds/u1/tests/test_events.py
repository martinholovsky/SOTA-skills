"""Event dispatcher tests."""

import pytest
from reportkit.events import EventRegistry


def test_handler_called_on_dispatch():
    registry = EventRegistry()
    received = []

    @registry.handler("report.created")
    def on_created(payload):
        received.append(payload)

    registry.dispatch("report.created", {"report_id": "abc"})
    assert len(received) == 1
    assert received[0]["report_id"] == "abc"


def test_multiple_handlers_all_called():
    registry = EventRegistry()
    log = []

    registry.register("report.deleted", lambda p: log.append("h1"))
    registry.register("report.deleted", lambda p: log.append("h2"))

    registry.dispatch("report.deleted", {})
    assert log == ["h1", "h2"]


def test_no_handlers_no_error():
    registry = EventRegistry()
    # Should not raise
    registry.dispatch("unknown.event", {"x": 1})


def test_failing_handler_does_not_block_others():
    registry = EventRegistry()
    log = []

    def bad_handler(payload):
        raise RuntimeError("boom")

    def good_handler(payload):
        log.append("ok")

    registry.register("test.event", bad_handler)
    registry.register("test.event", good_handler)

    registry.dispatch("test.event", {})
    assert log == ["ok"]


def test_dispatch_fires_on_create_report(svc, editor_token):
    from tests.conftest import make_request
    from reportkit.events import default_registry

    fired = []
    default_registry.register("report.created", lambda p: fired.append(p))

    svc.create_report(make_request(editor_token, body={"title": "Event Test"}))
    assert len(fired) == 1
    assert fired[0]["title"] == "Event Test"


def test_dispatch_fires_on_delete_report(svc, admin_token):
    from tests.conftest import make_request
    from reportkit.events import default_registry

    create_resp = svc.create_report(
        make_request(admin_token, body={"title": "To Delete"})
    )
    report_id = create_resp["report"]["id"]

    fired = []
    default_registry.register("report.deleted", lambda p: fired.append(p))

    svc.delete_report(make_request(admin_token), report_id)
    assert len(fired) == 1
    assert fired[0]["report_id"] == report_id
