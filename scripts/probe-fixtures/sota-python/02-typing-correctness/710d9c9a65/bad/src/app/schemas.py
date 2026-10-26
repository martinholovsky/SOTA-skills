from pydantic import BaseModel, ConfigDict


class SignupIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    email: str
