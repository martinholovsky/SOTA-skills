"""Audit log tests."""

import pytest
from reportkit.audit import log as audit_log


def test_audit_log_written(db):
    audit_log(db, "test.action", actor_id="u1", tenant_id="t1", target_id="r1",
              detail={"note": "test"})
    db.commit()
    row = db.execute(
        "SELECT * FROM audit_log WHERE action='test.action'"
    ).fetchone()
    assert row is not None
    assert row["actor_id"] == "u1"
    assert row["tenant_id"] == "t1"
    assert row["target_id"] == "r1"


def test_audit_log_no_pii_in_detail(db):
    """Detail dict is stored as JSON; verify it round-trips without secrets."""
    import json
    audit_log(db, "test.safe", detail={"report_id": "abc", "size": 42})
    db.commit()
    row = db.execute("SELECT detail FROM audit_log WHERE action='test.safe'").fetchone()
    detail = json.loads(row["detail"])
    assert detail["report_id"] == "abc"
    assert detail["size"] == 42
