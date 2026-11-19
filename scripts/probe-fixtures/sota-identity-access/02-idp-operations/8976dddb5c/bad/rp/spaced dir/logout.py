def backchannel_logout(form):
    claims = verify_jwt(form["logout_token"], typ="logout+jwt")
    end_sessions(claims["sid"])
