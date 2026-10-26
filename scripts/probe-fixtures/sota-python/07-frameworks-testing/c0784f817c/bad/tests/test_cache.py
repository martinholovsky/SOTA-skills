import time


def test_expires():
    c = Cache(ttl=1)
    c.put("k", 1)
    time.sleep(1.1)
    assert c.get("k") is None
