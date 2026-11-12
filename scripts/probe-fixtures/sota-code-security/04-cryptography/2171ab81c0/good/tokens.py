import secrets


def reset_token():
    return secrets.token_urlsafe(32)
