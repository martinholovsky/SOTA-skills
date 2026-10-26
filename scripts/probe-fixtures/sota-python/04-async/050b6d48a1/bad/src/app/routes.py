import httpx


async def proxy(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)
