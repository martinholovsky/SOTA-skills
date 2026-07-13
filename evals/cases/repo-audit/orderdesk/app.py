"""Application wiring: middleware, routers, error handling."""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import admin, orders, profile, reset, search
from .config import settings

log = logging.getLogger("orderdesk")


def create_app() -> FastAPI:
    app = FastAPI(title="orderdesk")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    @app.middleware("http")
    async def enforce_body_limit(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > settings.max_body_bytes:
            return JSONResponse({"detail": "payload too large"}, status_code=413)
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000"
        return response

    @app.exception_handler(Exception)
    async def on_error(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internals to the client; log the detail server-side.
        log.exception("unhandled error on %s", request.url.path)
        return JSONResponse({"detail": "internal error"}, status_code=500)

    # User-facing routers authenticate per-route via require_user.
    app.include_router(orders.router)
    app.include_router(search.router)
    app.include_router(profile.router)
    app.include_router(reset.router)
    # Administrative router (cross-tenant operations).
    app.include_router(admin.router)
    return app


app = create_app()
