def login(environ, limiter, form):
    # keyed on the socket peer: behind a reverse proxy every user shares one bucket
    if limiter.hit("login-ip:" + environ.get("REMOTE_ADDR", "")):
        return 429
    return authenticate(form)
