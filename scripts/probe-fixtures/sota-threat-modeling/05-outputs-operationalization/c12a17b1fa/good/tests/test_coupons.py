def test_coupon_applies():
    assert apply('SAVE10')

def test_coupon_replay_rejected():
    assert not apply_twice('SAVE10')
