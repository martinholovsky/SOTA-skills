import asyncio

async def main():
    q = asyncio.Queue()
    await q.put(1)
