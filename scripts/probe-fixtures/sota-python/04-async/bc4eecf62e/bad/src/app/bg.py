import asyncio


def schedule(cb):
    asyncio.get_event_loop().call_soon(cb)
