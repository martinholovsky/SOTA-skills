@app.patch("/me")
def update_me():
    user = User(**request.json)
    db.merge(user)
