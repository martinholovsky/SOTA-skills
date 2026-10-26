from psycopg import sql

def use_tenant(conn, tenant):
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(tenant)))
