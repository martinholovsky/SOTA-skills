from dataclasses import dataclass, field
from pydantic import SecretStr

@dataclass
class Creds:
    user: str
    password: str = field(default='', repr=False)
    token_count: int = 0
    api_key: SecretStr = SecretStr('')
