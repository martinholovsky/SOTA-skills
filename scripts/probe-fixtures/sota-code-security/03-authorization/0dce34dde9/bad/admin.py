@app.post("/admin/users/<uid>/disable")
def disable(uid):
    if session["role"] != "admin":
        abort(403)
    users.disable(uid)
