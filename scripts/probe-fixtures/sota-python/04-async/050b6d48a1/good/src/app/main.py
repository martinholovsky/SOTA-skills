import contextlib

import httpx


@contextlib.asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=10) as app.state.http:
        yield
