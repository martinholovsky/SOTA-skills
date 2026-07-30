"""Report read/write service."""
from reportkit import permissions


class NotAllowed(Exception):
    pass


class ReportService:
    def __init__(self, db):
        self.db = db

    def get(self, actor_id, report_id):
        """Fetch a single report for the caller."""
        if not permissions.has_permission(self.db, actor_id, "report:read"):
            raise NotAllowed("missing report:read")
        return self.db.fetch_report(report_id)

    def list_mine(self, actor_id):
        if not permissions.has_permission(self.db, actor_id, "report:read"):
            raise NotAllowed("missing report:read")
        return self.db.list_reports_for_owner(actor_id)

    def search(self, actor_id, term, sort="created_at"):
        if not permissions.has_permission(self.db, actor_id, "report:read"):
            raise NotAllowed("missing report:read")
        return self.db.search_reports(actor_id, term, sort)

    def delete(self, actor_id, report_id):
        if not permissions.has_permission(self.db, actor_id, "report:delete"):
            raise NotAllowed("missing report:delete")
        row = self.db.fetch_report(report_id)
        if row is None:
            return False
        _id, owner_id, _tenant, _title, _body = row
        if owner_id != actor_id:
            raise NotAllowed("not the owner")
        cur = self.db._conn.cursor()
        cur.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self.db._conn.commit()
        self.db.record_audit_entry(actor_id, f"deleted report {report_id}")
        return True
