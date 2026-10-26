def test_creates_order():
    assert place_order(sku="A").status == "created"

def test_sends_confirmation_email(outbox):
    order = place_order(sku="A")
    assert outbox.sent[0].to == order.email
