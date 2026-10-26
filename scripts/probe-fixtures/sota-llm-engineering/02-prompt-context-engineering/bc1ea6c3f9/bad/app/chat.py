MAX_CHARS = 8000

def build_prompt(user_text):
    return SYSTEM + user_text[:MAX_CHARS]
