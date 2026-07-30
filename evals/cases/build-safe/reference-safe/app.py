"""HTTP entrypoints.

Routes authenticate the caller, then delegate to a service. Events raised by the
routes are dispatched through the handler registry.
"""
from reportkit import handlers, permissions, uploads
from reportkit.handlers import report_events  # noqa: F401  (registration)
# No tenant.quota_exceeded handler: nothing dispatches that event (config.EMITTED_EVENTS),
# and a handler nothing can reach reads as coverage it does not provide.
from reportkit.reports import NotAllowed, ReportService


class Http:
    def __init__(self, db, storage, session_store):
        self.db = db
        self.storage = storage
        self.sessions = session_store
        self.reports = ReportService(db)

    def _actor(self, request):
        token = request["headers"].get("Authorization", "").removeprefix("Bearer ")
        user_id = self.sessions.resolve(token)
        if user_id is None:
            raise NotAllowed("not authenticated")
        return user_id

    def get_report(self, request, report_id):
        actor = self._actor(request)
        row = self.reports.get(actor, report_id)
        if row is None:
            return {"status": 404}
        _id, _owner, _tenant, title, body = row
        return {"status": 200, "body": {"id": _id, "title": title, "body": body}}

    def list_reports(self, request):
        actor = self._actor(request)
        return {"status": 200, "body": self.reports.list_mine(actor)}

    def search_reports(self, request):
        actor = self._actor(request)
        term = request["query"].get("q", "")
        sort = request["query"].get("sort", "created_at")
        return {"status": 200, "body": self.reports.search(actor, term, sort)}

    def create_report(self, request):
        actor = self._actor(request)
        if not permissions.has_permission(self.db, actor, "report:write"):
            return {"status": 403}
        cur = self.db._conn.cursor()
        cur.execute(
            "INSERT INTO reports (owner_id, title, body) VALUES (?, ?, ?)",
            (actor, request["body"]["title"], request["body"]["body"]),
        )
        self.db._conn.commit()
        new_id = cur.lastrowid
        handlers.dispatch("report.created", {"report_id": new_id})
        return {"status": 201, "body": {"id": new_id}}

    def delete_report(self, request, report_id):
        actor = self._actor(request)
        ok = self.reports.delete(actor, report_id)
        if ok:
            handlers.dispatch("report.deleted", {"report_id": report_id})
        return {"status": 200 if ok else 404}

    def upload_attachment(self, request):
        actor = self._actor(request)
        if not permissions.has_permission(self.db, actor, "report:write"):
            return {"status": 403}
        name = request["body"]["filename"]
        payload = request["body"]["content"]
        return {"status": 201, "body": uploads.store(self.storage, name, payload)}
