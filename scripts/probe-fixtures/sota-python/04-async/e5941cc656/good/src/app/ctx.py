from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id")


async def middleware(req, call_next):
    token = request_id.set(req.headers["x-request-id"])
    try:
        return await call_next(req)
    finally:
        request_id.reset(token)
