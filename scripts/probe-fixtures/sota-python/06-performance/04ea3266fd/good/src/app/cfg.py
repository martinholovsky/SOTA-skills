from functools import lru_cache


@lru_cache(maxsize=1)
def settings():
    return load()
