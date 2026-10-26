from flask import request

def get_profile():
    user_id = parse_user_id(request.args["user"])  # digits only, else 400
    return mc.get("profile:%d" % user_id)
