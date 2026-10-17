"""Tests for the event registry."""

import pytest
from reportkit.events import EventRegistry


class TestEventRegistry:
    def test_handler_called_on_dispatch(self):
        reg = EventRegistry()
        received = []

        @reg.on("report.created")
        def handler(payload):
            received.append(payload)

        reg.dispatch("report.created", {"report_id": "x"})
        assert received == [{"report_id": "x"}]

    def test_multiple_handlers_all_called(self):
        reg = EventRegistry()
        log = []
        reg.register("report.deleted", lambda p: log.append("a"))
        reg.register("report.deleted", lambda p: log.append("b"))
        reg.dispatch("report.deleted", {})
        assert log == ["a", "b"]

    def test_no_handlers_is_silent(self):
        reg = EventRegistry()
        reg.dispatch("unknown.event", {})  # must not raise

    def test_failing_handler_does_not_abort_others(self):
        reg = EventRegistry()
        log = []

        def bad(payload):
            raise RuntimeError("boom")

        def good(payload):
            log.append("ok")

        reg.register("ev", bad)
        reg.register("ev", good)
        reg.dispatch("ev", {})
        assert log == ["ok"]

    def test_dispatch_fires_domain_events_from_service(self):
        """Integration: service dispatches report.created."""
        from reportkit.fixtures import build_fixture_db
        from reportkit.service import ReportService

        conn, ctx = build_fixture_db()
        reg = EventRegistry()
        fired = []
        reg.register("report.created", lambda p: fired.append(p))

        svc = ReportService(conn, registry=reg)
        tok = ctx["tokens"]["editor"]
        svc.create_report({
            "headers": {"Authorization": f"Bearer {tok}"},
            "body": {"title": "Event Test"},
            "query": {},
        })
        assert len(fired) == 1
        assert fired[0]["tenant_id"] == ctx["tenant_id"]
