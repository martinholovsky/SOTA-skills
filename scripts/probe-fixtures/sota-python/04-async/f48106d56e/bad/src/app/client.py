import requests


async def lookup(url):
    return requests.get(url, timeout=5).json()
