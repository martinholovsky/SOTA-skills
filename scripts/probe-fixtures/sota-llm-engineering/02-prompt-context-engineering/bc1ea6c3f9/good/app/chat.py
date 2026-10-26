MAX_TOKENS = 2000

def build_prompt(user_text):
    if count_tokens(user_text) > MAX_TOKENS:
        raise InputTooLong(MAX_TOKENS)
    return SYSTEM + user_text
