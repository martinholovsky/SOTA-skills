def use_tenant(conn, tenant):
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {tenant}, public")
