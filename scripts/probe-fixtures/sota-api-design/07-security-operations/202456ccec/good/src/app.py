def login(principal, limiter, form):
    # keyed on the account: no network address involved
    if limiter.hit("login-account:" + form["username"].lower()):
        return 429
    return authenticate(form)
