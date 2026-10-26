import httpx


async def lookup(client: httpx.AsyncClient, url):
    return (await client.get(url)).json()
