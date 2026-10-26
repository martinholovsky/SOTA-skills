from typing import TypedDict, Unpack


class Opts(TypedDict, total=False):
    timeout: float


def fetch(url: str, **kwargs: Unpack[Opts]) -> bytes:
    return b""
