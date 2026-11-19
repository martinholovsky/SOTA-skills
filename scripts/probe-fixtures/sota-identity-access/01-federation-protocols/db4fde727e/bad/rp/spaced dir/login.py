def start(session):
    return authorize_url(scope="openid", acr_values="phr", max_age=300)

def callback(id_token):
    return id_token["sub"]
