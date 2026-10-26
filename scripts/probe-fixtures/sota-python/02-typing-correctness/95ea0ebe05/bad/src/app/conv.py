def to_int(raw: str) -> int:
    if not raw:
        return -1
    try:
        return int(raw)
    except ValueError:
        return -1
