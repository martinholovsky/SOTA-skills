def test_creates_order_and_sends_email(outbox):
    order = place_order(sku="A")
    assert order.status == "created"
    assert outbox.sent[0].to == order.email
