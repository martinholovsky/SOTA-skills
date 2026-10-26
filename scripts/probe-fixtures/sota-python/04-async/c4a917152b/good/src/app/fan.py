import asyncio


async def fetch_all(urls):
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(get(u)) for u in urls]
    return [t.result() for t in tasks]
