"""Shared pytest fixtures."""
import pytest
from reportkit.db import connect, apply_schema
from reportkit.service import ReportService
from reportkit import fixtures as F


@pytest.fixture()
def conn():
    c = connect(":memory:")
    apply_schema(c)
    return c


@pytest.fixture()
def svc(conn):
    return ReportService(conn)


@pytest.fixture()
def tenant(conn):
    return F.make_tenant(conn, "TestCo")


@pytest.fixture()
def viewer(conn, tenant):
    uid = F.make_user(conn, tenant, role="viewer")
    token = F.make_session(conn, uid)
    return uid, token


@pytest.fixture()
def editor(conn, tenant):
    uid = F.make_user(conn, tenant, role="editor")
    token = F.make_session(conn, uid)
    return uid, token


@pytest.fixture()
def admin(conn, tenant):
    uid = F.make_user(conn, tenant, role="admin")
    token = F.make_session(conn, uid)
    return uid, token


def req(token: str, body=None, query=None) -> dict:
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body":    body or {},
        "query":   query or {},
    }
