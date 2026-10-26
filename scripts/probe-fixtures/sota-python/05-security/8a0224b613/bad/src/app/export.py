def export(data):
    with open("/tmp/export.csv", "w", encoding="utf-8") as fh:
        fh.write(data)
