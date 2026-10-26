import time


def timed(fn):
    start = time.time()
    fn()
    return time.time() - start
