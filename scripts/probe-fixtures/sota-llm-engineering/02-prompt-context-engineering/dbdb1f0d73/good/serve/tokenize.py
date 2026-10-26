import tiktoken
enc = tiktoken.get_encoding("o200k_base")

def encode_user(text):
    return enc.encode(text, disallowed_special=())
