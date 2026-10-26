@app.post("/reset")
def reset():
    user = User.find_by_login(request.form["login"])
    if user:
        send_reset_email(user.email, issue_reset_token(user))
    return "", 202
