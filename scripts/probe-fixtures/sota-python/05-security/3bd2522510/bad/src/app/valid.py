import re


def valid_username(name):
    return re.match(r"[a-z0-9_]{3,20}", name) is not None
