from pydantic import BaseModel


class ScoreResponse(BaseModel):
    score: float
    predicted_ethnicity: str
