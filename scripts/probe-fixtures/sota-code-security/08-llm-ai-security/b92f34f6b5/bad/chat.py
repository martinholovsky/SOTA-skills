@app.post("/chat")
def chat():
    messages = request.json["messages"]
    return llm.complete(messages)
