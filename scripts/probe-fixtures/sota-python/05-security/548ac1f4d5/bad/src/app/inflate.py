import zlib


def inflate(data: bytes) -> bytes:
    return zlib.decompress(data)
