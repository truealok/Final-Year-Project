"""Simple in-memory sliding-window rate limiter.

Rate-limiting *ready*: disabled by default via ``RATE_LIMIT_ENABLED``.
For multi-instance deployments swap the in-memory store for Redis without
touching the rest of the application.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.max_requests = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        client_key = request.client.host if request.client else "anonymous"
        now = time.monotonic()
        hits = self._hits[client_key]

        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - hits[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry later.",
                        "details": None,
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)
