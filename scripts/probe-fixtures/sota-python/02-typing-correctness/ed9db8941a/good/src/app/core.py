from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    qty: int


def total(orders: list[Order]) -> int:
    return sum(o.qty for o in orders)
