def test_encrypt_round_trip():
    box = Envelope(key=KEY)
    assert box.decrypt(box.encrypt(b"hello")) == b"hello"
