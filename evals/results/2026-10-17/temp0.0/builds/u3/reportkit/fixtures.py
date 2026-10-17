"""
Test / development fixture helpers.

Creates a minimal in-memory database populated with:
  - one tenant
  - three users (viewer, editor, admin)
  - live sessions for each
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from .db import apply_schema, open_db
from .ids import new_id


def _future(days: int = 1) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%fZ")


def build_fixture_db() -> tuple[sqlite3.Connection, dict]:
    """
    Return ``(conn, ctx)`` where *ctx* holds IDs and tokens for tests.
    """
    conn = open_db(":memory:")
    apply_schema(conn)

    tenant_id = new_id()
    conn.execute(
        "INSERT INTO tenants (id, name) VALUES (?, ?)",
        (tenant_id, "Acme Corp"),
    )

    users = {}
    tokens = {}
    for role in ("viewer", "editor", "admin"):
        uid = new_id()
        conn.execute(
            "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
            (uid, tenant_id, f"{role}_user", role),
        )
        tok = f"token-{role}-{uid[:8]}"
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (tok, uid, _future()),
        )
        users[role] = uid
        tokens[role] = tok

    conn.commit()

    ctx = {
        "tenant_id": tenant_id,
        "users":     users,
        "tokens":    tokens,
    }
    return conn, ctx
