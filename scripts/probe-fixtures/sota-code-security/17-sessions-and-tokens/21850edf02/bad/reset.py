@app.post("/reset/start")
def reset_start():
    user = User.by_email(request.form["email"])
    session["user_id"] = user.id
    send_reset_code(user)
