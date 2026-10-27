import zlib

MAX_OUT = 10 * 1024 * 1024


def inflate(data: bytes) -> bytes:
    d = zlib.decompressobj()
    out = d.decompress(data, MAX_OUT)
    if d.unconsumed_tail:
        raise ValueError("decoded size over budget")
    return out
