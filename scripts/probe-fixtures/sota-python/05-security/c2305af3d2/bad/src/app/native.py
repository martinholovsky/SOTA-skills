import ctypes

lib = ctypes.CDLL("libfast.so")


def fast(buf, n):
    return lib.process(buf, n)
