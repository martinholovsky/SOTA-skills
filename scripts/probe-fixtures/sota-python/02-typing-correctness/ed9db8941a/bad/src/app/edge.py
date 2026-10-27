from pydantic import BaseModel, TypeAdapter


class Order(BaseModel):
    qty: int


ORDERS = TypeAdapter(list[Order])


def load(raw: bytes) -> list[Order]:
    return ORDERS.validate_json(raw)


def one(raw: dict) -> Order:
    return Order.model_validate(raw)
