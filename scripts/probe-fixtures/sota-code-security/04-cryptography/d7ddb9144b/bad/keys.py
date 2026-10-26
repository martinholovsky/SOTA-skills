from cryptography.hazmat.primitives.asymmetric import rsa

signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
