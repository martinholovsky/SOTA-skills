from compression import zstd


def pack(b):
    return zstd.compress(b)
