"""Core report CRUD operations."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .auth import authenticate, require_permission
from .events import default_registry

# Allowed sort columns for search — validated against a whitelist to prevent
# SQL injection from user-supplied sort values.
_ALLOWED_SORT_COLUMNS = {"created_at", "title"}
_DEFAULT_SORT = "created_at"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _report_row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ---------------------------------------------------------------------------
# Public handlers
# ---------------------------------------------------------------------------

def create_report(conn: sqlite3.Connection, request: dict) -> dict:
    """
    POST /reports

    request body keys: title (required), body (optional)
    """
    user = authenticate(conn, request)
    require_permission(user, "report:write")

    body_data: dict = request.get("body") or {}
    title: str = (body_data.get("title") or "").strip()
    if not title:
        return {"status": 400, "error": "title is required"}

    report_body: str = body_data.get("body") or ""
    report_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """
        INSERT INTO reports (id, tenant_id, owner_id, title, body, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (report_id, user["tenant_id"], user["user_id"], title, report_body, now, now),
    )
    conn.commit()

    default_registry.dispatch(
        "report.created",
        {
            "report_id": report_id,
            "tenant_id": user["tenant_id"],
            "owner_id":  user["user_id"],
            "title":     title,
        },
    )

    row = conn.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    return {"status": 201, "report": _report_row_to_dict(row)}


def get_report(conn: sqlite3.Connection, request: dict, report_id: str) -> dict:
    """GET /reports/<report_id>"""
    user = authenticate(conn, request)
    require_permission(user, "report:read")

    row = conn.execute(
        "SELECT * FROM reports WHERE id = ? AND tenant_id = ?",
        (report_id, user["tenant_id"]),
    ).fetchone()

    if row is None:
        return {"status": 404, "error": "Report not found"}

    return {"status": 200, "report": _report_row_to_dict(row)}


def list_reports(conn: sqlite3.Connection, request: dict) -> dict:
    """
    GET /reports

    Returns the caller's own reports, newest first.

    The permissions check is the hottest query in the service; the
    session resolution already joins users → tenants in a single query
    (see auth.resolve_session), so no extra round-trip is needed here.
    """
    user = authenticate(conn, request)
    require_permission(user, "report:read")

    rows = conn.execute(
        """
        SELECT * FROM reports
        WHERE owner_id = ? AND tenant_id = ?
        ORDER BY created_at DESC
        """,
        (user["user_id"], user["tenant_id"]),
    ).fetchall()

    return {"status": 200, "reports": [_report_row_to_dict(r) for r in rows]}


def search_reports(conn: sqlite3.Connection, request: dict) -> dict:
    """
    GET /reports/search?q=...&sort=created_at|title

    Title search across the caller's own reports.
    The sort column comes from request["query"]["sort"] and is validated
    against a whitelist before being interpolated into SQL.
    """
    user = authenticate(conn, request)
    require_permission(user, "report:read")

    query_params: dict = request.get("query") or {}
    search_term: str = (query_params.get("q") or "").strip()

    raw_sort: str = (query_params.get("sort") or _DEFAULT_SORT).strip()
    # Whitelist validation — never interpolate user input directly.
    sort_col = raw_sort if raw_sort in _ALLOWED_SORT_COLUMNS else _DEFAULT_SORT
    sort_dir = "ASC" if sort_col == "title" else "DESC"

    if not search_term:
        return {"status": 400, "error": "query parameter 'q' is required"}

    # Use FTS for title search; join back to reports for full row data.
    # The FTS table stores owner_id and tenant_id to avoid a second join.
    rows = conn.execute(
        f"""
        SELECT r.*
        FROM reports_fts f
        JOIN reports r ON r.id = f.report_id
        WHERE f.reports_fts MATCH ?
          AND f.owner_id  = ?
          AND f.tenant_id = ?
        ORDER BY r.{sort_col} {sort_dir}
        """,
        (search_term, user["user_id"], user["tenant_id"]),
    ).fetchall()

    return {"status": 200, "reports": [_report_row_to_dict(r) for r in rows]}


def delete_report(
    conn: sqlite3.Connection, request: dict, report_id: str
) -> dict:
    """DELETE /reports/<report_id>"""
    user = authenticate(conn, request)
    require_permission(user, "report:delete")

    row = conn.execute(
        "SELECT id, tenant_id FROM reports WHERE id = ? AND tenant_id = ?",
        (report_id, user["tenant_id"]),
    ).fetchone()

    if row is None:
        return {"status": 404, "error": "Report not found"}

    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()

    default_registry.dispatch(
        "report.deleted",
        {
            "report_id": report_id,
            "tenant_id": user["tenant_id"],
            "deleted_by": user["user_id"],
        },
    )

    return {"status": 200, "deleted": report_id}
