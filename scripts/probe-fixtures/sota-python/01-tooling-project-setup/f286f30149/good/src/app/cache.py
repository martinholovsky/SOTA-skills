_cache = {}


def get(key):
    return _cache.setdefault(key, compute(key))
