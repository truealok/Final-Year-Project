"""Request logging middleware."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import get_logger

logger = get_logger("resilichain.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one structured line per request: method, path, status, duration."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        user_id = getattr(request.state, "user_id", None) or "-"
        logger.info(
            "%s %s -> %s (%.1f ms) user=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            user_id,
        )
        return response
