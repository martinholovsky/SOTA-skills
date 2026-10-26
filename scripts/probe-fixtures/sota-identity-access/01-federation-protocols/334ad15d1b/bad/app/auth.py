def current_user(claims):
    return db.users.find_one({"sub": claims["sub"]})
