import asyncio


class State:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
