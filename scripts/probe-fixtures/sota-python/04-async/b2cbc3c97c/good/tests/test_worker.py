import asyncio


async def test_worker_stops_on_cancel():
    t = asyncio.create_task(loop())
    await asyncio.sleep(0)
    t.cancel()
