@app.post("/account/recover")
def recover():
    start_password_reset(request.form["email"])
    return redirect("/check-your-inbox")
