from pydantic import BaseModel, SecretStr

class Login(BaseModel):
    password: SecretStr
