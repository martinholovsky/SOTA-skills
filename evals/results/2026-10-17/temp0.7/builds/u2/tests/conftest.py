"""Shared pytest fixtures."""

import pytest

from reportkit.db import open_db, apply_schema
from reportkit.service import ReportService
from reportkit.fixtures import make_tenant, make_user, make_session, make_report


@pytest.fixture()
def conn():
    db = open_db(":memory:")
    apply_schema(db)
    return db


@pytest.fixture()
def svc(conn):
    return ReportService(conn)


# ---------------------------------------------------------------------------
# A ready-made tenant with one user of each role
# ---------------------------------------------------------------------------

@pytest.fixture()
def tenant(conn):
    return make_tenant(conn, "TestCo")


@pytest.fixture()
def viewer_token(conn, tenant):
    uid = make_user(conn, tenant, role="viewer")
    return make_session(conn, uid)


@pytest.fixture()
def editor_token(conn, tenant):
    uid = make_user(conn, tenant, role="editor")
    return make_session(conn, uid)


@pytest.fixture()
def admin_token(conn, tenant):
    uid = make_user(conn, tenant, role="admin")
    return make_session(conn, uid)
