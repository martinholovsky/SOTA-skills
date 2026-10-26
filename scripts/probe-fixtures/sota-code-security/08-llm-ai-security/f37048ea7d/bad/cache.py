def lookup(prompt):
    cache_key = sha256_hex(prompt)
    return cache.get(cache_key)
