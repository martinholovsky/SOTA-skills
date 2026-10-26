from flask import request

def get_profile():
    return mc.get("profile:" + request.args["user"])
