def test_charges_card():
    gateway = FakePaymentGateway()
    bill(customer_id="c1", amount=500, gateway=gateway)
    assert gateway.charges == [("c1", 500)]
