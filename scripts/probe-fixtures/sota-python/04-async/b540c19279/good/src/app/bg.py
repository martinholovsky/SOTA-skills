import asyncio


async def handler(req):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(audit(req))
    return ok()
