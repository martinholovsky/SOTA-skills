def logout(claims):
    revoked.add((claims["iss"], claims["jti"]))
