"""Tests for the event registry."""

import pytest
from reportkit.events import EventRegistry


def test_handler_called(capsys):
    reg = EventRegistry()
    received = []

    @reg.on("report.created")
    def h(payload):
        received.append(payload)

    reg.dispatch("report.created", {"id": "1"})
    assert received == [{"id": "1"}]


def test_multiple_handlers_all_called():
    reg = EventRegistry()
    log = []

    reg.register("x", lambda p: log.append("a"))
    reg.register("x", lambda p: log.append("b"))

    reg.dispatch("x", {})
    assert log == ["a", "b"]


def test_no_handlers_no_error():
    reg = EventRegistry()
    reg.dispatch("unknown.event", {})  # should not raise


def test_failing_handler_does_not_block_next(capsys):
    reg = EventRegistry()
    log = []

    def bad(p):
        raise RuntimeError("boom")

    def good(p):
        log.append("ok")

    reg.register("ev", bad)
    reg.register("ev", good)

    reg.dispatch("ev", {})
    assert log == ["ok"]
    captured = capsys.readouterr()
    assert "boom" in captured.err


def test_dispatch_report_created_and_deleted():
    """Smoke-test the two application events."""
    reg = EventRegistry()
    seen = []
    reg.on("report.created")(lambda p: seen.append(("created", p["report_id"])))
    reg.on("report.deleted")(lambda p: seen.append(("deleted", p["report_id"])))

    reg.dispatch("report.created", {"report_id": "r1"})
    reg.dispatch("report.deleted", {"report_id": "r1"})

    assert seen == [("created", "r1"), ("deleted", "r1")]
