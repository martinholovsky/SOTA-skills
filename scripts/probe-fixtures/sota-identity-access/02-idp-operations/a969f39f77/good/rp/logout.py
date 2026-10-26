EVENT = "http://schemas.openid.net/event/backchannel-logout"

def backchannel_logout(form):
    claims = verify_jwt(form["logout_token"], typ="logout+jwt")
    if EVENT not in claims.get("events", {}) or "nonce" in claims:
        raise BadRequest()
    end_sessions(claims["sid"])
