def run_nightly_cleanup():
    actor = SYSTEM_IDENTITY  # explicit global-job identity, no tenant
    for tenant in tenants.all():
        purge_expired(tenant_id=tenant.id, actor=actor)
