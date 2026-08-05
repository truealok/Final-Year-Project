"""Application exception hierarchy.

Services and repositories raise these domain-level errors; the global
exception handlers (app.middleware.exception_handlers) translate them into
consistent JSON HTTP responses.
"""

from typing import Any


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    error_code: str = "internal_server_error"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"
    default_message = "The request is invalid."


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"
    default_message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "The request conflicts with the current state."


class UnprocessableEntityError(AppError):
    status_code = 422
    error_code = "unprocessable_entity"
    default_message = "The request could not be processed."
