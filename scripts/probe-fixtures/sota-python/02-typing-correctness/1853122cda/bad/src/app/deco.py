from collections.abc import Callable
from typing import Any


def logged(fn: Callable[..., Any]) -> Callable[..., Any]:
    return fn
