import functools

@functools.lru_cache(maxsize=None)
def user_segment(user_id):
    return compute(user_id)
