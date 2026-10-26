def test_expires(clock):
    c = Cache(ttl=1, clock=clock)
    c.put("k", 1)
    clock.advance(1.1)
    assert c.get("k") is None
