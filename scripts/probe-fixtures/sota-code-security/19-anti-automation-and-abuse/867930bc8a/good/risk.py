@app.before_request
def bot_gate():
    bot_score = score(request)
    if bot_score > 0.9:
        return respond_with_ladder(request, bot_score)  # log -> challenge -> tarpit -> hold
