def current_user(claims):
    return db.users.find_one({"iss": claims["iss"], "sub": claims["sub"]})
