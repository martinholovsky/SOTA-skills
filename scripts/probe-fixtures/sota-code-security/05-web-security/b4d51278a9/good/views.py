def page(body):
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp
