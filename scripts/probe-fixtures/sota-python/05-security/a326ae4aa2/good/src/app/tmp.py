import os
import tempfile


def scratch():
    fd, path = tempfile.mkstemp()
    return os.fdopen(fd, "w", encoding="utf-8")
