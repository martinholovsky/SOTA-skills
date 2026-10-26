def login(request, response, token):
    response.set_cookie("session", token)
    return response
