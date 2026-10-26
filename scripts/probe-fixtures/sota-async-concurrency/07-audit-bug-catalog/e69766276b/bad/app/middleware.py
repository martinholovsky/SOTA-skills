from contextvars import ContextVar

current_tenant = ContextVar("current_tenant")

async def tenant_mw(request, call_next):
    current_tenant.set(request.headers["X-Tenant"])
    return await call_next(request)
