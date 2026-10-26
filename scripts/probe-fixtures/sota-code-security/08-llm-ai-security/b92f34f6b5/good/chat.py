@app.post("/chat")
def chat():
    user_turn = request.json["message"]
    return llm.complete([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_turn}])
