def find_orders(cur, customer_id, status=None):
    sql = "SELECT * FROM orders WHERE 1=1"
    if status:
        sql += " AND status = '%s'" % status
    cur.execute(sql)
