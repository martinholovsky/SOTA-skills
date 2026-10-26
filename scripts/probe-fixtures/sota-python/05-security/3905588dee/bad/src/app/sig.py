import hashlib


def sign(data):
    return hashlib.md5(data).hexdigest()
