import secrets
import string


def reset_code():
    return "".join(secrets.choice(string.digits) for _ in range(6))
