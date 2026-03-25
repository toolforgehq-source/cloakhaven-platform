"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date
import uuid


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    display_name: Optional[str]
    date_of_birth: Optional[date]
    email_verified: bool
    subscription_tier: str
    subscription_status: str
    is_profile_claimed: bool
    profile_visibility: str

    model_config = {"from_attributes": True}


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
