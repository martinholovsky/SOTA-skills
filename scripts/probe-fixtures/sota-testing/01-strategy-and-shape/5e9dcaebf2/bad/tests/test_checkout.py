from unittest import mock

def test_total_applies_discount():
    pricing = mock.Mock()
    pricing.discount_for.return_value = 10
    cart = mock.Mock(items=[100])
    assert Checkout(pricing, cart).total() == 90
