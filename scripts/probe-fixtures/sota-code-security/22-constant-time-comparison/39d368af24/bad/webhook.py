def verify(body, signature):
    expected = hmac.new(SECRET, body, "sha256").hexdigest()
    if signature == expected:
        return True
    return False
