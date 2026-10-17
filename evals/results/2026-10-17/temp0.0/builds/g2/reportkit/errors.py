"""Typed error hierarchy for reportkit."""


class ReportkitError(Exception):
    """Base class."""
    http_status: int = 500
    code: str = "internal_error"


class BadRequest(ReportkitError):
    http_status = 400
    code = "bad_request"


class Unauthorized(ReportkitError):
    http_status = 401
    code = "unauthorized"


class Forbidden(ReportkitError):
    http_status = 403
    code = "forbidden"


class NotFound(ReportkitError):
    http_status = 404
    code = "not_found"


class Conflict(ReportkitError):
    http_status = 409
    code = "conflict"


class TenantSuspended(ReportkitError):
    http_status = 403
    code = "tenant_suspended"


class RateLimited(ReportkitError):
    http_status = 429
    code = "rate_limited"


class PayloadTooLarge(ReportkitError):
    http_status = 413
    code = "payload_too_large"


class UnsupportedMediaType(ReportkitError):
    http_status = 415
    code = "unsupported_media_type"


class WebhookAuthFailed(ReportkitError):
    http_status = 401
    code = "webhook_auth_failed"
