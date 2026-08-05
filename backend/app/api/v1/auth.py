"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.dependencies import AuthServiceDep, CurrentUser
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import UserRead

router = APIRouter()


@router.post(
    "/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def signup(data: SignupRequest, service: AuthServiceDep) -> AuthResponse:
    """Register a new account. The first account created becomes admin."""
    user, tokens = await service.signup(data)
    return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, service: AuthServiceDep) -> AuthResponse:
    """Authenticate with email + password (JSON body)."""
    user, tokens = await service.login(data.email, data.password)
    return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post("/token", response_model=TokenPair, include_in_schema=True)
async def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> TokenPair:
    """OAuth2 form login (used by the Swagger 'Authorize' button).

    Enter your email address in the ``username`` field.
    """
    _user, tokens = await service.login(form.username, form.password)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenPair:
    """Exchange a valid refresh token for a new token pair (rotation)."""
    return await service.refresh(data.refresh_token)


@router.post("/logout", response_model=Message)
async def logout(user: CurrentUser, service: AuthServiceDep) -> Message:
    """Revoke the current user's refresh token."""
    await service.logout(user)
    return Message(message="Logged out successfully.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest, service: AuthServiceDep
) -> ForgotPasswordResponse:
    """Start a password reset.

    Always returns 200 to avoid revealing which emails exist. In development
    mode the reset token is returned directly (no email service configured).
    """
    token = await service.forgot_password(data.email)
    return ForgotPasswordResponse(
        message="If the email exists, a password reset has been initiated.",
        reset_token=token if settings.DEBUG else None,
    )


@router.post("/reset-password", response_model=Message)
async def reset_password(
    data: ResetPasswordRequest, service: AuthServiceDep
) -> Message:
    """Complete a password reset with the token from forgot-password."""
    await service.reset_password(data.token, data.new_password)
    return Message(message="Password has been reset. Please log in again.")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    """Return the currently authenticated user."""
    return UserRead.model_validate(user)
