from typing import Protocol


class Store(Protocol):
    def get(self, key: str) -> bytes: ...
