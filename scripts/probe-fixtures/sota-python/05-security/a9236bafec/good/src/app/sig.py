import hashlib


def etag(data):
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()
