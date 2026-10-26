@app.post("/transfer")
def transfer():
    return do_transfer(current_user, request.form)
