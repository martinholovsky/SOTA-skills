import asyncio


async def test_poller_fires(clock):
    p = start_poller(clock)
    clock.advance(0.5)
    await asyncio.sleep(0)
    assert p.fired
