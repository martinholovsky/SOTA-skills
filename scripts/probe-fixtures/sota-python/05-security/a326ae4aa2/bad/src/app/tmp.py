import tempfile


def scratch():
    path = tempfile.mktemp()
    return open(path, "w", encoding="utf-8")
