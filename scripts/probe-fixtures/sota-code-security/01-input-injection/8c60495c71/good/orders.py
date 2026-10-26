def find_orders(cur, customer_id, status=None):
    if status is None:
        cur.execute("SELECT * FROM orders WHERE customer_id = %s", (customer_id,))
    else:
        cur.execute("SELECT * FROM orders WHERE customer_id = %s AND status = %s",
                    (customer_id, status))
