@app.get("/preview")
def preview():
    r = requests.get(request.args["url"], timeout=5)
    return r.text
