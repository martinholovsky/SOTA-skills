from pathlib import Path

ROOT = Path("/srv/files").resolve()


def read(name):
    p = (ROOT / name).resolve()
    if not p.is_relative_to(ROOT):
        raise PermissionError(name)
    return p.read_bytes()
