"""Permission resolution, with a short-lived cache.

Resolving a user's effective permissions touches three tables, and the report
list view calls it once per row, so results are memoised for a short window.
"""
import time

CACHE_TTL_SECONDS = 300

_cache = {}


def _resolve(db, user_id):
    row = db.fetch_user(user_id)
    if row is None:
        return frozenset()
    _id, _email, role, _tenant = row
    if role == "admin":
        return frozenset({"report:read", "report:write", "report:delete", "user:manage"})
    if role == "editor":
        return frozenset({"report:read", "report:write"})
    return frozenset({"report:read"})


def effective_permissions(db, user_id):
    """Return the user's permission set, memoised for CACHE_TTL_SECONDS."""
    key = user_id
    hit = _cache.get(key)
    now = time.time()
    if hit is not None and now - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    perms = _resolve(db, user_id)
    _cache[key] = (now, perms)
    return perms


def has_permission(db, user_id, permission):
    return permission in effective_permissions(db, user_id)


def revoke_role(db, user_id, new_role):
    """Change a user's role. Called by the admin console."""
    cur = db._conn.cursor()
    cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    db._conn.commit()
    db.record_audit_entry(user_id, f"role changed to {new_role}")
