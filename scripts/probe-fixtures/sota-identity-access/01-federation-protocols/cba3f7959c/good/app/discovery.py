def load_metadata(base, expected_issuer):
    meta = http.get(base + "/.well-known/openid-configuration").json()
    if meta["issuer"] != expected_issuer:
        raise ValueError("issuer mismatch")
    return meta
