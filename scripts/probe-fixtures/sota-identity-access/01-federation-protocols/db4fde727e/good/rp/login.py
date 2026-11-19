def start(session):
    return authorize_url(scope="openid", acr_values="phr", max_age=300)

def callback(id_token):
    if id_token.get("acr") != "phr" or now() - id_token["auth_time"] > 300:
        raise StepUpRequired()
    return id_token["sub"]
