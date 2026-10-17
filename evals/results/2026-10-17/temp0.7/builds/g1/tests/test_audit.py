"""Audit log tests."""

import json
import pytest

from reportkit.audit import log as audit_log


class TestAuditLog:
    def test_writes_record(self, conn):
        audit_log(conn, action="test.action", actor_id="u1", tenant_id="t1",
                  target_type="report", target_id="r1",
                  detail={"key": "value"})
        row = conn.execute("SELECT * FROM audit_log WHERE action = 'test.action'").fetchone()
        assert row is not None
        assert row["actor_id"] == "u1"
        assert row["tenant_id"] == "t1"
        assert row["target_id"] == "r1"
        detail = json.loads(row["detail"])
        assert detail["key"] == "value"

    def test_null_actor_allowed(self, conn):
        audit_log(conn, action="system.event")
        row = conn.execute("SELECT * FROM audit_log WHERE action = 'system.event'").fetchone()
        assert row is not None
        assert row["actor_id"] is None

    def test_does_not_raise_on_error(self, conn):
        # Close the connection to provoke an error; audit must not raise.
        import sqlite3
        bad_conn = sqlite3.connect(":memory:")
        bad_conn.close()
        # Should not raise.
        audit_log(bad_conn, action="should.not.raise")
