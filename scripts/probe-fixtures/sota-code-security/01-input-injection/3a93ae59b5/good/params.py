from urllib.parse import parse_qs

def read_params(qs):
    params = parse_qs(qs)
    for name in ("account", "amount"):
        if len(params.get(name, [])) != 1:
            raise BadRequest("duplicate or missing %s" % name)
    return params["account"][0], params["amount"][0]
