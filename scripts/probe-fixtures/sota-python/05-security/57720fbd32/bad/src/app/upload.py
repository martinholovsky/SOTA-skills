from pathlib import Path

from werkzeug.utils import secure_filename

ROOT = Path("/srv/uploads").resolve()


def save(f) -> Path:
    dest = (ROOT / secure_filename(f.filename)).resolve()
    if not dest.is_relative_to(ROOT):
        raise ValueError("outside upload root")
    f.save(dest)
    return dest
