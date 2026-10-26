def answer(client, messages):
    resp = client.chat.completions.create(model=MODEL, messages=messages, logprobs=True)
    text = resp.choices[0].message.content
    if confidence(resp) < THRESHOLD:
        return FALLBACK
    return text
