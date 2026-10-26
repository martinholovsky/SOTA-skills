@app.post("/support/users/<uid>/password-reset")
@staff_only
def trigger_reset(uid):
    start_password_reset(User.get(uid))  # user picks the new password
