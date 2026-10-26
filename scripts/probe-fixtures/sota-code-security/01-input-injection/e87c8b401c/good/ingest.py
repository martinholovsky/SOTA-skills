def read_name(raw: bytes) -> str:
    text = raw.decode("utf-8")  # strict: UnicodeDecodeError -> 400
    if "\x00" in text:
        raise ValueError("NUL in field")
    return text
