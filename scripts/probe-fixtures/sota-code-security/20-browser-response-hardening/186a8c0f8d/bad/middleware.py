@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
