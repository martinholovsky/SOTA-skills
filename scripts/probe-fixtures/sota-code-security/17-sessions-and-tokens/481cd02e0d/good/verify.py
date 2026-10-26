jwks = jwt.PyJWKClient(ISSUER_JWKS_URL)

def verify(token):
    key = jwks.get_signing_key_from_jwt(token)
    return jwt.decode(token, key.key, algorithms=["ES256"], audience=AUD, issuer=ISSUER)
