from collections.abc import AsyncIterator


async def rows(conn) -> AsyncIterator[dict]:
    async with conn.cursor() as cur:
        async for r in cur:
            yield r


async def first(conn):
    async for r in rows(conn):
        return r
