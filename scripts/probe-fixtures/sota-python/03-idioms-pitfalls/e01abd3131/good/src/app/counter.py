import threading

_lock = threading.Lock()


def bump():
    with _lock:
        step()
