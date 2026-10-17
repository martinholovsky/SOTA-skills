"""
Immutable audit log writer.

Every admin mutation, authentication event, and security anomaly is written
here.  The detail column carries a JSON blob with no PII or secrets.
"""

import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


def log(
    conn: sqlite3.Connection,
    action: str,
    *,
    actor_id: str | None = None,
    tenant_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """
    Write an audit record.  Never raises; errors are logged to stderr only
    so that a failed audit write does not abort the primary operation.
    """
    try:
        detail_json = json.dumps(detail) if detail else None
        conn.execute(
            """
            INSERT INTO audit_log
                (actor_id, tenant_id, action, target_type, target_id, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_id, tenant_id, action, target_type, target_id, detail_json),
        )
    except Exception:
        logger.exception(
            "audit_write_failed action=%s actor=%s",
            action,
            actor_id,
        )
