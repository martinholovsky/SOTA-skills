from unittest import mock

@mock.patch("stripe.Charge.create")
def test_charges_card(create):
    bill(customer_id="c1", amount=500)
    create.assert_called_once()
