import asyncio


async def crawl(urls):
    async with asyncio.TaskGroup() as tg:
        for u in urls:
            tg.create_task(fetch(u))
