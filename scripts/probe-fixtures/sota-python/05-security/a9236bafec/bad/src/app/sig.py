import hashlib


def sign(data):
    return hashlib.sha1(data).hexdigest()
