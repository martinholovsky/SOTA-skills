def export_orders(rows, fh):
    for row in rows:
        fh.write(",".join(row) + "\n")
