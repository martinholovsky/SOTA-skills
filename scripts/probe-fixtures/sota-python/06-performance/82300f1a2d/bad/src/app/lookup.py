from functools import cache


@cache
def resolve(hostname):
    return dns(hostname)
