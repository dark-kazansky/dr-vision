"""
Auth models — Pydantic schemas for authentication.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Request models ---


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str = Field(min_length=1)


class CreateUserRequest(BaseModel):
    """Admin-only: create a new user."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="user", pattern=r"^(admin|user)$")


class UpdateUserRequest(BaseModel):
    """Admin-only: update user fields."""

    full_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default=None, pattern=r"^(admin|user)$")
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """Change own password."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


# --- Response models ---


class TokenResponse(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Public user info (no password hash)."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# --- Internal models ---


class UserInDB(BaseModel):
    """Full user record from database."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    password_hash: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str  # user_id
    email: str
    role: str
    type: str  # "access" or "refresh"
    exp: int
    iat: int
