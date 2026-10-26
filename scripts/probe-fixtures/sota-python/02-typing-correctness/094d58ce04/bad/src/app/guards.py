from typing import TypeGuard


def is_str_list(v: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in v)
