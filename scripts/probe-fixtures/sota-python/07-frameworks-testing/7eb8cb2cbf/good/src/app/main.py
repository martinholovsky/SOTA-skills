import contextlib

import httpx


@contextlib.asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient() as app.state.http:  # lifespan-scoped
        yield
