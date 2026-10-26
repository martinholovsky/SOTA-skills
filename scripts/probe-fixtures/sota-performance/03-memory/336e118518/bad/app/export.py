import json

def export(rows, fh):
    fh.write(json.dumps(rows))
