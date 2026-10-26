@app.post("/support/users/<uid>/password")
@staff_only
def set_pw(uid):
    User.get(uid).set_password(request.form["new_password"])
