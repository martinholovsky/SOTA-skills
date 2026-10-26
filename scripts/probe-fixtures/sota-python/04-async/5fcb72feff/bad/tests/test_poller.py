import asyncio


async def test_poller_fires():
    p = start_poller()
    await asyncio.sleep(0.5)
    assert p.fired
