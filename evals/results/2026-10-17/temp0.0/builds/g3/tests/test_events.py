"""
Tests for the event dispatcher.
"""

import pytest

from reportkit import events as ev


class TestDispatch:
    def test_registered_handler_called(self):
        calls = []
        ev.register("test.event", lambda p: calls.append(p))
        ev.dispatch("test.event", {"x": 1})
        assert any(c.get("x") == 1 for c in calls)

    def test_unknown_event_no_error(self):
        # Dispatching an event with no handlers must not raise.
        ev.dispatch("no.such.event.xyz", {})

    def test_handler_exception_does_not_propagate(self):
        def bad_handler(p):
            raise RuntimeError("boom")

        ev.register("test.bad", bad_handler)
        # Must not raise.
        ev.dispatch("test.bad", {})

    def test_multiple_handlers_all_called(self):
        results = []
        ev.register("test.multi", lambda p: results.append("a"))
        ev.register("test.multi", lambda p: results.append("b"))
        ev.dispatch("test.multi", {})
        assert "a" in results
        assert "b" in results

    def test_quota_exceeded_handler_suspends_tenant(self, db, tenant_a):
        ev.dispatch("tenant.quota_exceeded", {"db": db, "tenant_id": tenant_a})
        row = db.execute(
            "SELECT suspended FROM tenants WHERE id = ?", (tenant_a,)
        ).fetchone()
        assert row["suspended"] == 1
