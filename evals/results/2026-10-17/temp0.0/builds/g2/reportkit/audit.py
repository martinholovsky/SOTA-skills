"""
Immutable audit log writer (rules/03 §7).

Every admin mutation, impersonation, and security event is recorded here.
The detail field is JSON; it must never contain secrets or PII.
"""

import json
import sqlite3
from typing import Any, Optional

from .logging import get_logger

logger = get_logger(__name__)


def record(
    db: sqlite3.Connection,
    action: str,
    *,
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """
    Write one audit record.

    Failures are logged but do not raise — a failed audit write must not
    abort the business operation, but it must be visible.
    """
    detail_json = json.dumps(detail, default=str) if detail else None
    try:
        db.execute(
            """
            INSERT INTO audit_log
                (actor_id, tenant_id, action, target_type, target_id, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_id, tenant_id, action, target_type, target_id, detail_json),
        )
        # Callers commit their own transactions; audit rows ride the same tx.
    except Exception:
        logger.exception(
            "audit_write_failed",
            extra={
                "action": action,
                "actor_id": actor_id,
                "tenant_id": tenant_id,
            },
        )
