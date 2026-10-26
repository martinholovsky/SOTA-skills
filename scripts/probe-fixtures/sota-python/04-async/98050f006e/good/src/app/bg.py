import asyncio


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(refresh())
