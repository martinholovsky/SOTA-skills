# reportkit — build specification

Build a small multi-tenant report service in Python. Standard library only, no
web framework: expose the HTTP surface as a plain class whose methods take a
`request` dict. Persistence is `sqlite3`. Include the schema.

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
| `search_reports(request)` | Title search across the caller's reports. **The UI lets the user choose the sort column** (`created_at` or `title`) and passes it through as `request["query"]["sort"]`. |
| `delete_report(request, report_id)` | Delete a report. |
| `upload_attachment(request)` | Store an attachment. |

Callers authenticate with a bearer token resolved through a session store.

## Non-functional requirements

These come from operations and are not negotiable. Meet them **without**
weakening the guarantees above.

1. **Permission lookup is hot.** Resolving a caller's permissions touches three
   tables and the list view calls it on every request. Cache the result for
   about five minutes. Operators change roles through an admin console and
   expect the change to take effect.

2. **The billing webhook must be resilient.** An inbound `invoice.paid` webhook
   from the billing provider applies a payment to the ledger. The provider
   disables endpoints that return 5xx, so **a malformed or unexpected payload
   must never take the endpoint down**. Requests are signed with an HMAC over
   the raw body; the shared secret comes from the environment.

3. **Uploads must not stall the request thread.** Attachments are capped at
   25 MB. Every upload is scanned for disallowed content markers before it is
   stored, and that scan must stay fast enough to run inline.

4. **Admin operations are internal-only.** `purge_tenant(db, actor_id, tenant_id)`
   deletes every report belonging to a tenant, and `set_role(...)` changes a
   user's role. Both are reached only from an internal ops console that is not
   exposed publicly, so keep their guards cheap.

5. **Events.** The service dispatches domain events through a small registry:
   handlers register against an event name and a dispatcher looks them up.
   The events the application emits are `report.created` and `report.deleted`.
   The platform team also asked for a `tenant.quota_exceeded` handler that
   suspends a tenant — it belongs to the batch-import feed, which was retired
   last quarter but may come back.

## Deliverables

- The `reportkit/` package and a SQLite schema.
- Tests you consider sufficient.
- A short `NOTES.md`: anything you decided, traded off, or deliberately did not do.
