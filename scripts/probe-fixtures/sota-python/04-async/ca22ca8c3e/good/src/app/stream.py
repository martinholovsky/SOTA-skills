from collections.abc import AsyncIterator
from contextlib import aclosing


async def rows(conn) -> AsyncIterator[dict]:
    async with conn.cursor() as cur:
        async for r in cur:
            yield r


async def first(conn):
    async with aclosing(rows(conn)) as it:
        async for r in it:
            return r
