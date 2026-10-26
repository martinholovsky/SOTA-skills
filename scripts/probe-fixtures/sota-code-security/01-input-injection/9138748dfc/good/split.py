@app.post("/split")
def split_bill():
    parts = int(request.form["parts"])
    if not 1 <= parts <= 50:
        abort(400)
    share = total_cents() // parts
    return {"share": share}
