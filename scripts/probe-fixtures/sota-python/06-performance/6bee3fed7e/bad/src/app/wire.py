import gzip


def pack(b):
    return gzip.compress(b)
