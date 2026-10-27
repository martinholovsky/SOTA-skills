import requests

ALLOWED = {"api.example.com"}


def fetch(url: str) -> bytes:
    return requests.get(url, timeout=5).content
