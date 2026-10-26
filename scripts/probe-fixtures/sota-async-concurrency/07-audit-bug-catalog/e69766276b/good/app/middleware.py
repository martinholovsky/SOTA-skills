from contextvars import ContextVar

current_tenant = ContextVar("current_tenant")

async def tenant_mw(request, call_next):
    token = current_tenant.set(request.headers["X-Tenant"])
    try:
        return await call_next(request)
    finally:
        current_tenant.reset(token)
