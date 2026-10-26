from abc import ABC, abstractmethod


class Store(ABC):
    @abstractmethod
    def get(self, key: str) -> bytes: ...
