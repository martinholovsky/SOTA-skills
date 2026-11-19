import math


def parse_limit(raw):
    v = float(raw)
    if not math.isfinite(v):
        raise ValueError(raw)
    return v
