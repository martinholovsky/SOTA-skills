import functools


@functools.cache
def load_config(path):
    return read(path)
