def load(path):
    fh = open(path, encoding="utf-8")
    data = fh.read()
    fh.close()
    return data
