"""
ReportService — the public HTTP surface.

Each method takes a *request* dict and returns a *response* dict with at
least a ``status`` key (HTTP status code).

The class is a thin coordinator: it holds a database connection and delegates
to the domain modules.
"""

from __future__ import annotations

import sqlite3

from . import attachments, billing, reports
from .auth import AuthError
from .db import connect, init_schema


class ReportService:
    """
    Public HTTP surface for the report service.

    Parameters
    ----------
    db_path:
        Path passed to ``sqlite3.connect``.  Defaults to ``:memory:`` which
        is convenient for tests.
    conn:
        Pass an existing connection to share it (useful in tests).
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        conn: sqlite3.Connection | None = None,
    ) -> None:
        self._conn = conn if conn is not None else connect(db_path)
        init_schema(self._conn)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def create_report(self, request: dict) -> dict:
        return self._handle(reports.create_report, request)

    def get_report(self, request: dict, report_id: str) -> dict:
        return self._handle(reports.get_report, request, report_id)

    def list_reports(self, request: dict) -> dict:
        return self._handle(reports.list_reports, request)

    def search_reports(self, request: dict) -> dict:
        return self._handle(reports.search_reports, request)

    def delete_report(self, request: dict, report_id: str) -> dict:
        return self._handle(reports.delete_report, request, report_id)

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def upload_attachment(self, request: dict) -> dict:
        return self._handle(attachments.upload_attachment, request)

    # ------------------------------------------------------------------
    # Billing webhook (not in the public HTTP surface table but wired here
    # for completeness — the route handler calls this method)
    # ------------------------------------------------------------------

    def handle_billing_webhook(self, request: dict) -> dict:
        return self._handle(billing.handle_webhook, request)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle(self, fn, *args, **kwargs) -> dict:
        """
        Wrap a domain function call, converting AuthError to a response dict
        so callers always receive a well-formed response.
        """
        try:
            return fn(self._conn, *args, **kwargs)
        except AuthError as exc:
            return {"status": exc.status, "error": str(exc)}
