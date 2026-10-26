from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

def wrap_dek(kek, dek, iv):
    return AES.new(kek, AES.MODE_CBC, iv).encrypt(pad(dek, 16))
