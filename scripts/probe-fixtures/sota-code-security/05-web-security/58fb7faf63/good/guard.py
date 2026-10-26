@app.before_request
def csrf_guard():
    h = request.headers
    site = h.get("Sec-Fetch-Site")
    if site not in ("same-origin", "same-site", "cross-site", "none"):
        site = None
    if site == "same-origin":
        pass
    elif site is not None:
        abort(403)
    elif not source_origin_matches(request, EXPECTED_ORIGINS):
        abort(403)
