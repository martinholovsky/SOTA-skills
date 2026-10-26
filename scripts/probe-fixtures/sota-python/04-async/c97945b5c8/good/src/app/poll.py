import asyncio


async def poll():
    while True:
        await asyncio.sleep(1)
        await check()
