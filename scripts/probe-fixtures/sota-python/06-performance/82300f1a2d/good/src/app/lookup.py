from functools import lru_cache


@lru_cache(maxsize=1024)
def resolve(hostname):
    return dns(hostname)
