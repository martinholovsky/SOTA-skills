"""
Immutable audit log writer.

Rules applied
-------------
- rules/03 §7: every admin mutation has an immutable audit trail.
- rules/07 §2: security events logged with actor, target, and detail.
- Detail is a JSON blob; callers must pass IDs only — no secrets or PII.
"""

import json
import logging
import time

logger = logging.getLogger(__name__)


def log(
    db,
    action: str,
    *,
    actor_id: str | None = None,
    tenant_id: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """
    Insert one audit record.

    The audit_log table is INSERT-only (no UPDATE/DELETE in the schema).
    detail must contain no secrets or PII — callers pass IDs and
    human-readable event names only.
    """
    detail_json = json.dumps(detail or {})
    try:
        db.execute(
            """
            INSERT INTO audit_log(ts, actor_id, tenant_id, action, target_id, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(time.time()), actor_id, tenant_id, action, target_id, detail_json),
        )
        # Callers commit their own transactions; audit rows ride the same commit.
    except Exception:
        # Audit failure must not abort the main operation, but it must be
        # loud so on-call can investigate.
        logger.exception("audit_write_failed", extra={"action": action})
