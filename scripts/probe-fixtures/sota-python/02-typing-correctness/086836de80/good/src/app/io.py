from typing import Protocol


class ReaderProtocol(Protocol):
    def read(self) -> bytes: ...


def load(src: ReaderProtocol) -> bytes:
    return src.read()
