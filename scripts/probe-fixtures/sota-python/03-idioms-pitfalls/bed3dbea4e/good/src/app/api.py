import json


def _reject(c):
    raise ValueError(c)


def parse(body):
    return json.loads(body, parse_constant=_reject)
