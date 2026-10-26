import requests


def deliver(hook_url, payload):
    return requests.post(hook_url, json=payload, timeout=5)
