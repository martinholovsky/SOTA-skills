from typing import TypeVar

T = TypeVar("T")


def first(xs: list[T]) -> T:
    return xs[0]
