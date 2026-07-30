"""Database access layer.

A thin wrapper over the DB-API. Callers pass parameters; this module owns the
SQL text so query shapes stay auditable in one place.
"""


class Db:
    def __init__(self, conn):
        self._conn = conn

    def fetch_user(self, user_id):
        cur = self._conn.cursor()
        cur.execute("SELECT id, email, role, tenant_id FROM users WHERE id = ?", (user_id,))
        return cur.fetchone()

    def fetch_report(self, report_id):
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, owner_id, tenant_id, title, body FROM reports WHERE id = ?",
            (report_id,),
        )
        return cur.fetchone()

    def list_reports_for_owner(self, owner_id, limit=50):
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, title FROM reports WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        )
        return cur.fetchall()

    SORT_COLUMNS = {"created_at": "created_at", "title": "title"}

    def search_reports(self, owner_id, term, sort="created_at"):
        """Search a user's reports.

        `sort` is a column name chosen by the caller from a fixed set in the UI.
        """
        column = self.SORT_COLUMNS.get(sort)
        if column is None:
            raise ValueError(f"unsupported sort column: {sort}")
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT id, title FROM reports WHERE owner_id = ? AND title LIKE ? ORDER BY {column} DESC",
            (owner_id, f"%{term}%"),
        )
        return cur.fetchall()

    def record_audit_entry(self, actor_id, action):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO audit_log (actor_id, action, at) VALUES (?, ?, datetime('now'))",
            (actor_id, action),
        )
        self._conn.commit()
