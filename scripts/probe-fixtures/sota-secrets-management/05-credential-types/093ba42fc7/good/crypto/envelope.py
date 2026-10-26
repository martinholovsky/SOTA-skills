from cryptography.hazmat.primitives.keywrap import aes_key_wrap

def wrap_dek(kek, dek):
    return aes_key_wrap(kek, dek)
