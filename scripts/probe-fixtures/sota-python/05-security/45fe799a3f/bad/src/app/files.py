from pathlib import Path

ROOT = Path("/srv/files")


def read(name):
    return (ROOT / name).read_bytes()
