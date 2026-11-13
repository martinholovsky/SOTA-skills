from dataclasses import dataclass


def connect(
    host: str,
    api_key: str,
    password: str | None = None,
) -> None:
    pass


@dataclass
class TokenInfo:
    token_type: str = "Bearer"
    client_secret_env: str = "APP_CLIENT_SECRET"
    password_hash: str = ''
    token_url: str = ''
