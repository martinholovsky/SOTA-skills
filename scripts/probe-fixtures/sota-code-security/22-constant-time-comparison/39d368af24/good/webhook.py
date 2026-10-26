def verify(body, signature):
    expected = hmac.new(SECRET, body, "sha256").hexdigest()
    return hmac.compare_digest(signature, expected)
