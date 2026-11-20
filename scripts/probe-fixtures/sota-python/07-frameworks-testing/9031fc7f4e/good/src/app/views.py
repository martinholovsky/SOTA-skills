def login(request, response, token):
    response.set_cookie("session", token, secure=True, httponly=True, samesite="lax")
    return response
