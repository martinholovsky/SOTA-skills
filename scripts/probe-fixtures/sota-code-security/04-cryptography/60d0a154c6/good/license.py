from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def store_api_secret(db, kek: bytes, nonce: bytes, value: bytes) -> None:
    db.save("api_key_sealed", nonce + AESGCM(kek).encrypt(nonce, value, b"api-v1"))
