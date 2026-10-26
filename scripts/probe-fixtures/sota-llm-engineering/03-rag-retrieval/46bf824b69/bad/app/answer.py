def answer(client, messages):
    resp = client.chat.completions.create(model=MODEL, messages=messages)
    return resp.choices[0].message.content
