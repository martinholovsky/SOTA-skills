import os


def save(path, key):
    with open(path, "wb") as fh:
        fh.write(key)
    os.chmod(path, 0o600)
