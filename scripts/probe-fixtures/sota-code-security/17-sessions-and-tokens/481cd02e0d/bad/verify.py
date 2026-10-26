def verify(token):
    header = jwt.get_unverified_header(token)
    key = fetch_jwks(header["jku"])
    return jwt.decode(token, key, algorithms=["RS256", "ES256"])
