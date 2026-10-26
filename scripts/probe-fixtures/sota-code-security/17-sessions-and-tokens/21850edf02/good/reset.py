@app.post("/reset/start")
def reset_start():
    user = User.by_email(request.form["email"])
    session["reset_subject"] = user.id
    send_reset_code(user)
