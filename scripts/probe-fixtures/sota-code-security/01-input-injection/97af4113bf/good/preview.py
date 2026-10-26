FEEDS = {"status": "https://status.example.com/feed.json"}

@app.get("/preview")
def preview():
    r = requests.get(FEEDS[request.args["feed"]], timeout=5, allow_redirects=False)
    return {"title": r.json()["title"]}
