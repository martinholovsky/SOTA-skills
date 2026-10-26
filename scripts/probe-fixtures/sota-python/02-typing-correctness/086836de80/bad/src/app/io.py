from typing import Protocol, runtime_checkable


@runtime_checkable
class ReaderProtocol(Protocol):
    def read(self) -> bytes: ...


def load(src):
    if isinstance(src, ReaderProtocol):
        return src.read()
