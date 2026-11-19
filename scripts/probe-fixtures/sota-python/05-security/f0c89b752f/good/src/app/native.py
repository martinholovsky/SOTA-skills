import ctypes

lib = ctypes.CDLL("libfast.so")
lib.process.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
lib.process.restype = ctypes.c_int


def fast(buf: bytes) -> int:
    return lib.process(buf, len(buf))
