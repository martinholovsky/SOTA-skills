import hashlib


def etag(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()
