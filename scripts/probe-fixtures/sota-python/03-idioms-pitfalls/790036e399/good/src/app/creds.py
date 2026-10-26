from dataclasses import dataclass, field


@dataclass
class Creds:
    user: str
    password: str = field(repr=False)
