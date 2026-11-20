def events_for(tenant_id, actor_id):
    return db.execute("SELECT * FROM audit_log WHERE tenant_id = %s AND actor_id = %s", (tenant_id, actor_id))
