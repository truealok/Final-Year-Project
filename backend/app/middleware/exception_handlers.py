"""Global exception handlers - every error becomes a consistent JSON shape:

    {"error": {"code": "...", "message": "...", "details": ...}}

Covers 400 / 401 / 403 / 404 / 409 / 422 / 429 / 500.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.exceptions import AppError
from app.utils.logger import get_logger

logger = get_logger("resilichain.errors")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return _error_response(
        exc.status_code, exc.error_code, exc.message, exc.details, headers
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    headers = getattr(exc, "headers", None)
    return _error_response(
        exc.status_code, "http_error", str(exc.detail), headers=headers
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg"),
         "type": err.get("type")}
        for err in exc.errors()
    ]
    return _error_response(
        422, "validation_error", "Request validation failed.", details
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    logger.warning("Integrity error on %s: %s", request.url.path, exc)
    return _error_response(
        409, "conflict", "The request conflicts with existing data."
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error_response(
        500, "internal_server_error", "An unexpected error occurred."
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
