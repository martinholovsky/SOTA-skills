def read_name(raw: bytes) -> str:
    return raw.decode("utf-8", errors="ignore")
