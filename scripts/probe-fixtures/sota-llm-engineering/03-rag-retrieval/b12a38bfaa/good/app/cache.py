def remember(key, answer, source):
    semantic_cache.set(key, answer, ttl=ttl_for(source.sensitivity))
