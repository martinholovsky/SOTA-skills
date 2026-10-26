def set_tenant(conn, tenant_id):
    # caller holds an open transaction; context dies with it
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
