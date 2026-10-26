from decimal import Decimal


def charge(price: Decimal, qty: int) -> Decimal:
    return price * qty
