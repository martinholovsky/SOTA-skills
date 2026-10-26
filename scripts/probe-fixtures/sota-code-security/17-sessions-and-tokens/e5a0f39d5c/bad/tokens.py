def issue(claims):
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")
