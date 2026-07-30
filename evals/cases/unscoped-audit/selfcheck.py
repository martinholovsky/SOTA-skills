#!/usr/bin/env python3
"""Prove this fixture still has the defects its ground truth claims.

A fixture that quietly loses a planted defect keeps producing plausible recall
numbers while measuring nothing — the failure class the library calls a silent
control. So every claim in cases/unscoped-audit.jsonl that CAN be demonstrated at
runtime is demonstrated here, not asserted from the source text.

Run: python3 evals/cases/unscoped-audit/selfcheck.py   (exit 0 = fixture intact)
"""
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reportkit import admin, handlers, permissions, uploads, webhooks  # noqa: E402
from reportkit.db import Db  # noqa: E402
from reportkit.handlers import quota_events, report_events  # noqa: E402,F401
from reportkit.reports import ReportService  # noqa: E402

FAIL = []


def ok(label, condition, detail=""):
    print(f"  {'ok  ' if condition else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        FAIL.append(label)


def fresh_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, role TEXT, tenant_id INTEGER);
        CREATE TABLE reports (id INTEGER PRIMARY KEY, owner_id INTEGER, tenant_id INTEGER,
                              title TEXT, body TEXT, created_at TEXT DEFAULT '2026-01-01');
        CREATE TABLE audit_log (actor_id INTEGER, action TEXT, at TEXT);
        INSERT INTO users (id, email, role, tenant_id) VALUES (1, 'a@x', 'admin', 10);
        INSERT INTO users (id, email, role, tenant_id) VALUES (2, 'b@x', 'viewer', 20);
        INSERT INTO reports (id, owner_id, tenant_id, title, body) VALUES (99, 1, 10, 't', 'secret');
        """
    )
    permissions._cache.clear()
    return Db(conn)


print("unscoped-audit fixture selfcheck")

# control: IDOR — user 2 reads user 1's report through the service
db = fresh_db()
row = ReportService(db).get(2, 99)
ok("idor_get_report", row is not None and row[1] == 1,
   "viewer 2 read report owned by 1")

# control: SQLi — the sort parameter reaches ORDER BY unparameterized
db = fresh_db()
try:
    db.search_reports(1, "t", sort="created_at DESC, (SELECT 1)")
    injected = True
except sqlite3.Error:
    injected = False
ok("sqli_sort", injected, "attacker-shaped sort string was executed as SQL")

# treatment: swallowed webhook verification — a wrong signature still applies
class Ledger:
    def __init__(self):
        self.paid = []

    def mark_paid(self, invoice_id, cents):
        self.paid.append((invoice_id, cents))


ledger = Ledger()
res = webhooks.handle(b'{"type":"invoice.paid","invoice_id":"i1","amount_cents":500}',
                      {"X-Signature": "not-even-close"}, ledger)
ok("swallowed_webhook_verify", res["applied"] and ledger.paid,
   "event applied despite an invalid signature")

# treatment: unreached handler — registered, but the event is never emitted
from reportkit import config  # noqa: E402

registered = handlers.registered()
ok("unreached_quota_handler",
   "tenant.quota_exceeded" in registered and "tenant.quota_exceeded" not in config.EMITTED_EVENTS,
   f"registered={registered}, emitted={list(config.EMITTED_EVENTS)}")

# treatment: stale permission cache — role revoked, permissions unchanged
db = fresh_db()
before = permissions.has_permission(db, 1, "user:manage")
permissions.revoke_role(db, 1, "viewer")
after = permissions.has_permission(db, 1, "user:manage")
ok("stale_permission_cache", before and after,
   "still admin after revoke_role (cache keyed on user_id only)")

# treatment: truncation before inspection — marker past the scan window is stored
payload = (b"A" * (uploads.SCAN_LIMIT_BYTES + 10)) + b"<?php evil ?>"
ok("truncated_upload_scan", uploads.scan(payload) is True,
   f"banned marker at byte {uploads.SCAN_LIMIT_BYTES + 10} passed the scan")

# treatment: assert-as-control — the admin guard disappears under -O
probe = f"""
import sys; sys.path.insert(0, {HERE!r})
import sqlite3
from reportkit.db import Db
from reportkit import admin, permissions
conn = sqlite3.connect(":memory:")
conn.executescript('''
 CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, role TEXT, tenant_id INTEGER);
 CREATE TABLE reports (id INTEGER PRIMARY KEY, owner_id INTEGER, tenant_id INTEGER,
                       title TEXT, body TEXT, created_at TEXT);
 CREATE TABLE audit_log (actor_id INTEGER, action TEXT, at TEXT);
 INSERT INTO users VALUES (2, 'b@x', 'viewer', 20);
 INSERT INTO reports VALUES (5, 2, 20, 't', 'b', '2026-01-01');
''')
permissions._cache.clear()
admin.purge_tenant(Db(conn), 2, 20)   # actor 2 is a VIEWER, not an admin
print("PURGED")
"""
normal = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
optimized = subprocess.run([sys.executable, "-O", "-c", probe], capture_output=True, text=True)
ok("assert_authz_purge",
   normal.returncode != 0 and optimized.returncode == 0 and "PURGED" in optimized.stdout,
   "non-admin blocked normally, purge SUCCEEDS under python -O")

print()
if FAIL:
    print(f"FAIL: {len(FAIL)} planted defect(s) no longer behave as the ground truth claims: {FAIL}")
    sys.exit(1)
print("PASS: fixture intact (7 planted defects, 6 demonstrated at runtime).")
