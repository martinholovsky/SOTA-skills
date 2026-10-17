"""Test-fixture helpers — create tenants, users, sessions in an in-memory DB."""
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta


def make_tenant(conn: sqlite3.Connection, name: str = "Acme") -> str:
    tid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, name) VALUES (?, ?)", (tid, name)
    )
    conn.commit()
    return tid


def make_user(
    conn: sqlite3.Connection,
    tenant_id: str,
    role: str = "viewer",
    username: str | None = None,
) -> str:
    uid = str(uuid.uuid4())
    username = username or f"user_{uid[:8]}"
    conn.execute(
        "INSERT INTO users (id, tenant_id, username, role) VALUES (?, ?, ?, ?)",
        (uid, tenant_id, username, role),
    )
    conn.commit()
    return uid


def make_session(
    conn: sqlite3.Connection,
    user_id: str,
    ttl_seconds: int = 3600,
) -> str:
    token = str(uuid.uuid4())
    expires = (
        datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    ).strftime("%Y-%m-%dT%H:%M:%fZ")
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires),
    )
    conn.commit()
    return token


def make_report(
    conn: sqlite3.Connection,
    tenant_id: str,
    owner_id: str,
    title: str = "Test Report",
    body: str = "",
) -> str:
    rid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO reports (id, tenant_id, owner_id, title, body)
        VALUES (?, ?, ?, ?, ?)
        """,
        (rid, tenant_id, owner_id, title, body),
    )
    conn.commit()
    return rid
