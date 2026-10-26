import asyncio


async def handler(req):
    asyncio.create_task(audit(req))
    return ok()
