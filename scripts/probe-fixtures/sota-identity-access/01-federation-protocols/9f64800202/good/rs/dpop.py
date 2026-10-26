def verify_dpop(proof, method, url, token):
    hdr, claims = decode(proof)
    assert hdr["typ"] == "dpop+jwt"
    assert claims["htm"] == method and claims["htu"] == url
    assert claims["ath"] == b64url(sha256(token))
    return claims
