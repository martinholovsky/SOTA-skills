"""Domain exceptions."""


class ReportkitError(Exception):
    """Base class for all reportkit errors."""
    http_status: int = 500


class AuthenticationError(ReportkitError):
    http_status = 401


class AuthorisationError(ReportkitError):
    http_status = 403


class NotFoundError(ReportkitError):
    http_status = 404


class ValidationError(ReportkitError):
    http_status = 400


class ConflictError(ReportkitError):
    http_status = 409


class ContentPolicyError(ReportkitError):
    http_status = 422
