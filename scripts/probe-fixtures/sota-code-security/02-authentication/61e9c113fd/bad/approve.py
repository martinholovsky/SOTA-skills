@app.post("/transfers/<tid>/confirm")
def confirm(tid):
    method = request.json.get("mfa_method", "sms")
    return challenge(current_user, tid, method)
