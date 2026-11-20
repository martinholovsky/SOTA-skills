import requests


def rate():
    return requests.get("https://fx.example/rate").json()
