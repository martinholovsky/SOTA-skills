from dataclasses import dataclass


@dataclass
class Signer:
    signing_key: str
    credential: bytes
    passphrase: str = ''
