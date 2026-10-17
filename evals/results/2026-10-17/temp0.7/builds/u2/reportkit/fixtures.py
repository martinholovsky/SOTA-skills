"""Test fixture helpers — create tenants, users, sessions, reports in a db."""

import uuid
from datetime import datetime, timedelta, timezone


def _now_plus(seconds: int = 3600) -> str:
    dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def make_tenant(conn, name: str = "Acme") -> str:
    tid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tenants (id, name) VALUES (?, ?)", (tid, name)
    )
    conn.commit()
    return tid


def make_user(conn, tenant_id: str, role: str = "editor", email: str | None = None) -> str:
    uid = str(uuid.uuid4())
    email = email or f"{uid[:8]}@example.com"
    conn.execute(
        "INSERT INTO users (id, tenant_id, email, role) VALUES (?, ?, ?, ?)",
        (uid, tenant_id, email, role),
    )
    conn.commit()
    return uid


def make_session(conn, user_id: str, expires_in: int = 3600) -> str:
    token = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, _now_plus(expires_in)),
    )
    conn.commit()
    return token


def make_report(conn, owner_id: str, tenant_id: str, title: str = "Report") -> str:
    rid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO reports (id, tenant_id, owner_id, title, body)
        VALUES (?, ?, ?, ?, '')
        """,
        (rid, tenant_id, owner_id, title),
    )
    conn.commit()
    return rid


def bearer(token: str) -> dict:
    """Return a minimal request dict with an Authorization header."""
    return {"headers": {"Authorization": f"Bearer {token}"}}
