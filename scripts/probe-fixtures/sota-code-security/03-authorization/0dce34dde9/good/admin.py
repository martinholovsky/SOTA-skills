@app.post("/admin/users/<uid>/disable")
def disable(uid):
    if not authz.has_role(current_user_id(), "admin"):  # re-read per request
        abort(403)
    users.disable(uid)
