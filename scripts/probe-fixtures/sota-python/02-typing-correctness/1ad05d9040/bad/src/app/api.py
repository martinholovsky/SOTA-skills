from pydantic import BaseModel, ValidationError


class Order(BaseModel):
    qty: int


def parse(raw: dict) -> Order | None:
    try:
        return Order.model_validate(raw)
    except ValidationError:
        return None
