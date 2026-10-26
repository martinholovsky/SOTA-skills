import keyring

def save(tokens):
    keyring.set_password("mcp-client", "refresh_token", tokens.refresh)
