def run_nightly_cleanup():
    tenant_id = "system"
    purge_expired(tenant_id=tenant_id)
