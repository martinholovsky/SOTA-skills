def test_total_applies_discount():
    pricing = Pricing(discounts={"SPRING": 10})
    cart = Cart(items=[100], code="SPRING")
    assert Checkout(pricing, cart).total() == 90
