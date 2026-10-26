import re


def valid_username(name):
    return re.fullmatch(r"[a-z0-9_]{3,20}", name) is not None
