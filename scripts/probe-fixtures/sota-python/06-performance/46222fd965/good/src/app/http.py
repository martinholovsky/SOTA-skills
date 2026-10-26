SAFE = frozenset({"GET", "HEAD", "OPTIONS"})


def safe(method):
    return method in SAFE
