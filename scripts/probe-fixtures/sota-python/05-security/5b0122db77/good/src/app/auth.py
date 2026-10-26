import hmac


def verify(token, stored):
    return hmac.compare_digest(token, stored)
