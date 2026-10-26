import json

def export(rows, fh):
    json.dump(rows, fh)
