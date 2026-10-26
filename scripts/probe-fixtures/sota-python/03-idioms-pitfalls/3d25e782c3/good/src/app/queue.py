from collections import deque


def drain(items: deque):
    while items:
        handle(items.popleft())
