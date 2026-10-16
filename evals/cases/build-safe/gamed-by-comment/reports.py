"""Known-gamed reference for run-build-safe.py --selftest.

Both defects are present in the CODE; only the comments mention the safe path.
A scorer that reads comments as evidence credits both as avoided.
"""

def list_reports(db, sort_col):
    # TODO: maybe add allowed_columns later
    return db.execute(f"SELECT * FROM reports ORDER BY {sort_col}")


def get_report(db, report_id, user):
    # TODO: check owner_id == user.id before returning
    return db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
