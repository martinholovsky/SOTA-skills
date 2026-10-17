"""Domain exceptions used throughout reportkit."""


class ReportkitError(Exception):
    """Base class; carries an HTTP-ish status code."""
    status: int = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AuthenticationError(ReportkitError):
    status = 401


class PermissionError(ReportkitError):
    status = 403


class NotFoundError(ReportkitError):
    status = 404


class ConflictError(ReportkitError):
    status = 409


class ValidationError(ReportkitError):
    status = 422


class AttachmentTooLargeError(ValidationError):
    status = 413


class DisallowedContentError(ValidationError):
    status = 422


class WebhookSignatureError(ReportkitError):
    status = 400
