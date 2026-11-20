def cache_key_for(user_id):
    cache_key = f'pred:{MODEL_VERSION}:{user_id}'
    return cache_key
