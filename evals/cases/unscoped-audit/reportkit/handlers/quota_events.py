"""Handler for the tenant quota-exceeded event.

Suspends a tenant's uploads until an operator clears the flag.
"""
from reportkit.handlers import register


@register("tenant.quota_exceeded")
def on_quota_exceeded(payload):
    tenant = payload["tenant_id"]
    payload["suspend"](tenant)
    return {"suspended": tenant}
