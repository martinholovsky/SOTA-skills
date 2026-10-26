def name(v: object) -> str:
    if not isinstance(v, str):
        raise TypeError(v)
    return v
