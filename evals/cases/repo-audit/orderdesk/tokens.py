"""Small token / identifier helpers."""
import random
import string

_ALPHABET = string.ascii_letters + string.digits


def make_token(length: int = 32) -> str:
    """Return a random alphanumeric token of `length` characters."""
    return "".join(random.choice(_ALPHABET) for _ in range(length))
