"""Password hashing (bcrypt) and JWT creation / verification (PyJWT)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.utils.exceptions import UnauthorizedError


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# JWT tokens
# --------------------------------------------------------------------------- #
def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Create a signed JWT. Returns ``(token, jti)``."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
        **(extra_claims or {}),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token, jti


def create_access_token(subject: str, role: str) -> str:
    """Create a short-lived access token embedding the user's role."""
    token, _ = _create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role},
    )
    return token


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Create a long-lived refresh token. Returns ``(token, jti)``.

    The jti is persisted on the user so refresh tokens can be revoked
    (logout) and rotated on every refresh.
    """
    return _create_token(
        subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT, enforcing its ``type`` claim.

    Raises:
        UnauthorizedError: if the token is expired, malformed or of the
            wrong type.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Could not validate credentials.") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError(f"Invalid token type; expected '{expected_type}'.")
    return payload
