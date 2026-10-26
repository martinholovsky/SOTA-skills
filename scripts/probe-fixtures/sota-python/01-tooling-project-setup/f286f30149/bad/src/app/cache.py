_cache = {}


def get(key):
    if key not in _cache:
        _cache[key] = compute(key)
    return _cache[key]
