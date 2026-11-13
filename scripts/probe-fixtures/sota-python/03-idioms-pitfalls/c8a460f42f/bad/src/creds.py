from dataclasses import dataclass
from typing import Annotated, Optional

@dataclass
class Creds:
    user: str
    password: Optional[str] = None
    api_key: str | None = None
    private_key: Annotated[str, 'pem']
    pwd: str = ''
