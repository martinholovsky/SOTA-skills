"""
Shared test fixtures.
"""

import datetime
import hashlib
import uuid

import pytest

from reportkit.db import open_db
from reportkit.service import ReportService
from reportkit.rate_limit import RateLimiter


def _uuid() -> str:
    return str(uuid.uuid4())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture()
def db():
    """In-memory SQLite database with schema applied."""
    conn = open_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def service(db):
    """ReportService with a permissive rate limiter for tests."""
    rl = RateLimiter(window_seconds=60, max_requests=10_000)
    return ReportService(db, rate_limiter=rl)


@pytest.fixture()
def tenant_a(db):
    tid = _uuid()
    db.execute("INSERT INTO tenants (id) VALUES (?)", (tid,))
    db.commit()
    return tid


@pytest.fixture()
def tenant_b(db):
    tid = _uuid()
    db.execute("INSERT INTO tenants (id) VALUES (?)", (tid,))
    db.commit()
    return tid


def make_user(db, tenant_id: str, role: str = "editor") -> tuple[str, str]:
    """Insert a user and a valid session; return (user_id, bearer_token)."""
    user_id = _uuid()
    token = _uuid()
    token_hash = _hash_token(token)
    expires = (
        datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    ).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    db.execute(
        "INSERT INTO users (id, tenant_id, role) VALUES (?, ?, ?)",
        (user_id, tenant_id, role),
    )
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash, user_id, expires),
    )
    db.commit()
    return user_id, token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
