from urllib.parse import parse_qsl

def read_params(qs):
    params = dict(parse_qsl(qs))
    return params.get("account"), params.get("amount")
