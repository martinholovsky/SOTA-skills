import asyncio


async def fetch_all(urls):
    return await asyncio.gather(*(get(u) for u in urls))
