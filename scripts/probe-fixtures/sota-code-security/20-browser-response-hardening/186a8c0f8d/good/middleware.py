@app.before_request
def isolation():
    if request.headers.get("Sec-Fetch-Site") == "cross-site" and request.headers.get("Sec-Fetch-Mode") != "navigate":
        abort(403)
