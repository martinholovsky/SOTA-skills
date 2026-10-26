def page(body):
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/html"
    return resp
