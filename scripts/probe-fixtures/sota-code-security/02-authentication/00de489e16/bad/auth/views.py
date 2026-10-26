@app.post("/login/email")
def login_by_email():
    send_magic_link(request.form["email"])
    return redirect("/check-your-inbox")
