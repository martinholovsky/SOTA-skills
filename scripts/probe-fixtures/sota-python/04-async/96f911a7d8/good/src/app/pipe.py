import asyncio

async def main():
    q = asyncio.Queue(maxsize=100)
    await q.put(1)
