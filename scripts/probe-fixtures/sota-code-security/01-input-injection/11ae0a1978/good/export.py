import csv

def export_orders(rows, fh):
    writer = csv.writer(fh, quoting=csv.QUOTE_ALL)
    for row in rows:
        writer.writerow([neutralise_formula(v) for v in row])
