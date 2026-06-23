"""
Auth API router — login, refresh, user management.

Public endpoints:
    POST /auth/login      — authenticate and get tokens
    POST /auth/refresh    — refresh access token

Protected endpoints:
    GET  /auth/me         — get current user info
    PUT  /auth/me/password — change own password

Admin-only endpoints:
    POST /auth/users      — create user
    GET  /auth/users      — list users
    PUT  /auth/users/{id} — update user
    DELETE /auth/users/{id} — delete user
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth.dependencies import get_current_user, require_role
from auth.models import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    TokenResponse,
    UpdateUserRequest,
    UserInDB,
    UserResponse,
)
from auth.service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Public endpoints
# =============================================================================

import time

# Dictionary to track failed login attempts per IP. Format: {ip: [timestamp1, timestamp2, ...]}
_failed_login_attempts = {}

def _check_and_record_failed_attempt(ip: str):
    """Check if IP is rate limited (>= 10 failed attempts in last 15 minutes)."""
    now = time.time()
    
    # Clean up old attempts (> 15 minutes)
    global _failed_login_attempts
    _failed_login_attempts = {
        addr: [t for t in times if now - t < 900]
        for addr, times in _failed_login_attempts.items()
        if [t for t in times if now - t < 900]
    }
    
    attempts = _failed_login_attempts.get(ip, [])
    if len(attempts) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": "900"},
        )
    
    # Record the new failed attempt
    attempts.append(now)
    _failed_login_attempts[ip] = attempts

def _clear_failed_attempts(ip: str):
    """Clear failed attempts on successful login."""
    if ip in _failed_login_attempts:
        del _failed_login_attempts[ip]



@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest):
    """
    Authenticate with email + password, receive JWT tokens.

    Returns access_token (30min) and refresh_token (7 days).
    """
    auth_repo = getattr(request.app.state, "auth_repo", None)
    if auth_repo is None or auth_repo.pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    client_ip = request.client.host if request.client else "unknown"
    
    # 1. Check rate limit before validating credentials
    # Just checking length, we don't record a failure yet
    now = time.time()
    recent_attempts = [t for t in _failed_login_attempts.get(client_ip, []) if now - t < 900]
    if len(recent_attempts) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": "900"},
        )

    user_data = await auth_repo.get_user_by_email(body.email)
    if user_data is None:
        _check_and_record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user_data.get("is_active", False):
        _check_and_record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    if not AuthService.verify_password(body.password, user_data["password_hash"]):
        _check_and_record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Successful login: clear failed attempts
    _clear_failed_attempts(client_ip)

    user = UserInDB(**user_data)
    access_token, refresh_token, expires_in = AuthService.create_tokens(user)

    # Update last_login
    await auth_repo.update_last_login(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request):
    """
    Refresh access token using a valid refresh token.

    Send refresh_token in Authorization: Bearer header.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    token = auth_header[7:]
    payload = AuthService.decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    auth_repo = getattr(request.app.state, "auth_repo", None)
    if auth_repo is None or auth_repo.pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    user_data = await auth_repo.get_user_by_id(payload.sub)
    if user_data is None or not user_data.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    user = UserInDB(**user_data)
    access_token, refresh_token_new, expires_in = AuthService.create_tokens(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_new,
        expires_in=expires_in,
    )


# =============================================================================
# Protected endpoints (any authenticated user)
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.put("/me/password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    """Change own password."""
    if not AuthService.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash = AuthService.hash_password(body.new_password)
    auth_repo = request.app.state.auth_repo
    await auth_repo.update_user(current_user.id, password_hash=new_hash)

    return {"message": "Password changed successfully"}


# =============================================================================
# Admin-only endpoints
# =============================================================================


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    admin: UserInDB = Depends(require_role("admin")),
):
    """Admin-only: create a new user."""
    auth_repo = request.app.state.auth_repo

    # Check if email already exists
    existing = await auth_repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    password_hash = AuthService.hash_password(body.password)
    user_data = await auth_repo.create_user(
        email=body.email,
        full_name=body.full_name,
        password_hash=password_hash,
        role=body.role,
    )

    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        role=user_data["role"],
        is_active=user_data["is_active"],
        created_at=user_data["created_at"],
        last_login=user_data.get("last_login"),
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    admin: UserInDB = Depends(require_role("admin")),
):
    """Admin-only: list all users."""
    auth_repo = request.app.state.auth_repo
    users = await auth_repo.list_users(limit=limit, offset=offset)
    return [
        UserResponse(
            id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            is_active=u["is_active"],
            created_at=u["created_at"],
            last_login=u.get("last_login"),
        )
        for u in users
    ]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    body: UpdateUserRequest,
    admin: UserInDB = Depends(require_role("admin")),
):
    """Admin-only: update user fields (name, role, active status)."""
    auth_repo = request.app.state.auth_repo

    updated = await auth_repo.update_user(
        user_id,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=updated["id"],
        email=updated["email"],
        full_name=updated["full_name"],
        role=updated["role"],
        is_active=updated["is_active"],
        created_at=updated["created_at"],
        last_login=updated.get("last_login"),
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: str,
    admin: UserInDB = Depends(require_role("admin")),
):
    """Admin-only: delete a user."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    auth_repo = request.app.state.auth_repo
    deleted = await auth_repo.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
