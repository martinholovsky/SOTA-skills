import tarfile


def unpack(path, dest):
    with tarfile.open(path) as tf:
        tf.extractall(dest, filter="data")
