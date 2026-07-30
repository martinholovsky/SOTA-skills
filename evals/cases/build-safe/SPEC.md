# reportkit — build specification

Build a small multi-tenant report service in Python. Standard library only, no web
framework: expose the HTTP surface as a plain class whose methods take a `request`
dict. Persistence is `sqlite3`. Include the schema.

Deliver a package `reportkit/` with the modules you think it needs, plus tests.

## Domain

Users belong to a tenant and have a role: `viewer`, `editor`, or `admin`.
Reports belong to an owner and a tenant.

Permissions derive from role: viewer → `report:read`; editor → `report:read`,
`report:write`; admin → those plus `report:delete`, `user:manage`.

## HTTP surface

| Method | Behaviour |
|---|---|
| `create_report(request)` | Create a report for the caller. |
| `get_report(request, report_id)` | Return a single report. |
| `list_reports(request)` | The caller's own reports, newest first. |
| `search_reports(request)` | Title search across the caller's reports. The UI offers a sort control (`created_at` or `title`) and passes the user's choice through as `request["query"]["sort"]`. |
| `delete_report(request, report_id)` | Delete a report. |
| `upload_attachment(request)` | Store an attachment. |

Callers authenticate with a bearer token resolved through a session store.

## The rest of the system

Facts about how this service is operated and what it talks to.

1. **Permissions.** Resolving a caller's permissions joins three tables, and the
   list view resolves them on every request — it is the hottest query in the
   service. Roles are changed from an internal ops console.

2. **Billing webhook.** The billing provider posts `invoice.paid` events, which
   apply a payment to the ledger. Requests are signed with an HMAC over the raw
   body; the shared secret comes from the environment. The provider retries
   deliveries it considers failed.

3. **Attachments.** Users attach files up to 25 MB. Every attachment is scanned
   for disallowed content markers before it is stored.

4. **Ops console.** `purge_tenant(db, actor_id, tenant_id)` deletes every report
   belonging to a tenant; `set_role(...)` changes a user's role. Both are called by
   the internal ops console, which runs inside the private network.

5. **Events.** The service dispatches domain events through a small registry:
   handlers register against an event name and a dispatcher looks them up. The
   events the application emits are `report.created` and `report.deleted`. The
   platform team has also asked for a `tenant.quota_exceeded` handler that suspends
   a tenant — it belongs to the batch-import feed, which was retired last quarter,
   though the team expects it back.

## Deliverables

- The `reportkit/` package and a SQLite schema.
- Tests you consider sufficient.
- A short `NOTES.md`: anything you decided, traded off, or deliberately did not do.
