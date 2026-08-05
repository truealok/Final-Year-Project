"""Authentication context middleware.

Route *protection* is enforced by dependencies (``get_current_user`` /
``require_roles``). This middleware only decodes a bearer token, when
present, into ``request.state`` so logging and auditing can attribute
requests to a user - it never rejects a request itself.
"""

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.user_id = None
        request.state.user_role = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                payload = jwt.decode(
                    auth_header.removeprefix("Bearer ").strip(),
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role")
            except jwt.InvalidTokenError:
                pass  # invalid tokens are rejected later by the dependency

        return await call_next(request)
