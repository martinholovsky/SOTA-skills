from pydantic import BaseModel, ConfigDict, SecretStr

class Login(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    password: SecretStr
