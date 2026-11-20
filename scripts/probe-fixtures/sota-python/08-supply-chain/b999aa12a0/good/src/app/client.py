import requests


def rate():
    return requests.get("https://fx.example/rate", timeout=10).json()
