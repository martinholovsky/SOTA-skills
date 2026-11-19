from concurrent.futures import ThreadPoolExecutor

def test_encrypt_round_trip_concurrently():
    box = Envelope(key=KEY)
    msgs = [bytes([i]) * 32 for i in range(256)]
    with ThreadPoolExecutor(16) as pool:
        cts = list(pool.map(box.encrypt, msgs))
    assert [box.decrypt(c) for c in cts] == msgs
