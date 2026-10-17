"""
Tests for the audit log writer.
"""

import json

from reportkit.audit import record


class TestAuditRecord:
    def test_record_written(self, db, tenant_a):
        record(
            db,
            action="test.action",
            actor_id="actor-1",
            tenant_id=tenant_a,
            target_type="report",
            target_id="report-1",
            detail={"key": "value"},
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM audit_log WHERE action = 'test.action'"
        ).fetchone()
        assert row is not None
        assert row["actor_id"] == "actor-1"
        assert row["tenant_id"] == tenant_a
        assert row["target_type"] == "report"
        assert row["target_id"] == "report-1"
        detail = json.loads(row["detail"])
        assert detail["key"] == "value"

    def test_record_without_optional_fields(self, db):
        # Must not raise even with minimal arguments.
        record(db, action="minimal.action")
        db.commit()
        row = db.execute(
            "SELECT * FROM audit_log WHERE action = 'minimal.action'"
        ).fetchone()
        assert row is not None
        assert row["actor_id"] is None
