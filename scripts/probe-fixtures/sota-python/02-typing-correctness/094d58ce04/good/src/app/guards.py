from typing import TypeIs


def is_str(v: object) -> TypeIs[str]:
    return isinstance(v, str)
