from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id")


async def middleware(req, call_next):
    request_id.set(req.headers["x-request-id"])
    return await call_next(req)
