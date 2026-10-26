@app.post("/reset")
def reset():
    token = issue_reset_token(request.form["username"])
    send_reset_email(request.form["email"], token)
    return "", 202
