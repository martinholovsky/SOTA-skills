import uuid
from pathlib import Path

ROOT = Path("/srv/uploads")


def save(data: bytes) -> Path:
    dest = ROOT / f"{uuid.uuid4().hex}.bin"
    dest.write_bytes(data)
    return dest
