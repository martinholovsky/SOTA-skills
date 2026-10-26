from collections.abc import Callable


def logged[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    return fn
