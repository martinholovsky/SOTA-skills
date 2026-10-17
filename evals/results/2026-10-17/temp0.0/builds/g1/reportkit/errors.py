"""Typed HTTP-mapped exceptions."""

from __future__ import annotations


class AppError(Exception):
    status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str = "internal error") -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


class BadRequest(AppError):
    status = 400
    code = "bad_request"


class Unauthorized(AppError):
    status = 401
    code = "unauthorized"


class Forbidden(AppError):
    status = 403
    code = "forbidden"


class NotFound(AppError):
    status = 404
    code = "not_found"


class Conflict(AppError):
    status = 409
    code = "conflict"


class TenantSuspended(AppError):
    status = 403
    code = "tenant_suspended"


class RateLimited(AppError):
    status = 429
    code = "rate_limited"
