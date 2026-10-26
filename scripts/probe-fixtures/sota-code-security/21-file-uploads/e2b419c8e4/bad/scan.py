def scan(path):
    with open(path, "rb") as f:
        return requests.post("https://www.virustotal.com/api/v3/files", files={"file": f},
                             headers={"x-apikey": VT_KEY}).json()
