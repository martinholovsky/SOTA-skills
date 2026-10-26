import base64

def store_api_secret(db, secret: str) -> None:
    db.save("api_secret", base64.b64encode(secret.encode()))  # obfuscated at rest
