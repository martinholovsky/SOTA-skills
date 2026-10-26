import asyncio

sem = None


async def crawl(urls):
    limit = asyncio.Semaphore(20)

    async def one(u):
        async with limit:
            await fetch(u)

    async with asyncio.TaskGroup() as tg:
        for u in urls:
            tg.create_task(one(u))
