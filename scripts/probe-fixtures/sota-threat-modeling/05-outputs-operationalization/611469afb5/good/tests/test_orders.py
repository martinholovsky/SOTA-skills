def test_order_created():
    assert create_order()

def test_order_quota_exceeded():
    assert rejects()
