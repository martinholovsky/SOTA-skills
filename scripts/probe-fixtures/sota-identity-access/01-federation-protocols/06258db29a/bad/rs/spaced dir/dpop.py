def verify_dpop(proof, method, url, token):
    hdr, claims = decode(proof)
    assert hdr["typ"] == "dpop+jwt"
    assert claims["htm"] == method and claims["htu"] == url
    return claims
