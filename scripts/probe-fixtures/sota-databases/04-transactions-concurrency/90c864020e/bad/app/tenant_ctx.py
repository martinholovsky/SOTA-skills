def set_tenant(conn, tenant_id):
    with conn.cursor() as cur:
        cur.execute("SET app.tenant_id = %s", (tenant_id,))
