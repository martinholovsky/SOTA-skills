def lookup(tenant_id, prompt):
    cache_key = sha256_hex(tenant_id, prompt)
    return cache.get(cache_key)
