@app.before_request
def csrf_guard():
    site = request.headers.get("Sec-Fetch-Site", "same-origin")
    if site not in ("same-origin", "same-site"):
        abort(403)
