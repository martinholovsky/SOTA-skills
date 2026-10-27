import json

MAX_BODY = 1_000_000


def handle(body: bytes) -> dict:
    if len(body) > MAX_BODY:
        raise ValueError("body too large")
    return json.loads(body)
