"""Authentication endpoints."""

import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_verification_token,
    generate_password_reset_token,
)
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Simple in-memory rate limiter for auth endpoints
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 10  # max requests per window per IP


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = _rate_limit_store[client_ip]
    # Prune old entries
    _rate_limit_store[client_ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    _rate_limit_store[client_ip].append(now)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, raw_request: Request, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(raw_request)
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    verification_token = generate_verification_token()
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        display_name=request.display_name,
        date_of_birth=request.date_of_birth,
        email_verification_token=verification_token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, raw_request: Request, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(raw_request)
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email_verification_token == request.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    user.email_verified = True
    user.email_verification_token = None
    await db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest, raw_request: Request, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(raw_request)
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        token = generate_password_reset_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()
        # TODO: Send password reset email

    # Always return success to prevent email enumeration
    return MessageResponse(message="If the email exists, a password reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.password_reset_token == request.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    user.password_hash = hash_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()

    return MessageResponse(message="Password reset successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
