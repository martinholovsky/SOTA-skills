import functools

@functools.lru_cache(maxsize=None)
def user_segment(user_id, consent_version):
    return compute(user_id)
