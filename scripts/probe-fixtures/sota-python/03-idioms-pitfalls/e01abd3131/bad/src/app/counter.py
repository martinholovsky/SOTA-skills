import threading

_lock = threading.Lock()


def bump():
    _lock.acquire()
    step()
    _lock.release()
