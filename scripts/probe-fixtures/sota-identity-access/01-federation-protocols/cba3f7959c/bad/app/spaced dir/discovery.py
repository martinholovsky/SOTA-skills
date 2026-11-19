def load_metadata(base):
    meta = http.get(base + "/.well-known/openid-configuration").json()
    return meta
