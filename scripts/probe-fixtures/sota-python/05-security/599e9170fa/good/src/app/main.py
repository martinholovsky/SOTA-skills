def parse_id(raw: str) -> int:
    if len(raw) > 32:
        raise ValueError("id too long")
    return int(raw)
