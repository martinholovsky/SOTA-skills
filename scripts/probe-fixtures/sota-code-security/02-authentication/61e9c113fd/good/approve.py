@app.post("/transfers/<tid>/confirm")
def confirm(tid):
    method = policy.method_for(current_user, load_transfer(tid))  # server decides
    return challenge(current_user, tid, method)
