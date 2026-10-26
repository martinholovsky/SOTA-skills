@app.post("/split")
def split_bill():
    share = total_cents() / int(request.form["parts"])
    return {"share": share}
