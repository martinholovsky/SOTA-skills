import asyncio


async def schedule(cb):
    asyncio.get_running_loop().call_soon(cb)
