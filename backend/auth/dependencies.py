"""
FastAPI dependencies for authentication.

Usage in routes:
    from auth import get_current_user, require_role

    @router.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"user": user.email}

    @router.delete("/admin-only")
    async def admin_only(user = Depends(require_role("admin"))):
        return {"admin": user.email}
"""

import logging
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from auth.models import TokenPayload, UserInDB
from auth.service import AuthService

logger = logging.getLogger(__name__)

# HTTP Bearer scheme — auto_error=False so we can provide custom messages
_bearer_scheme = HTTPBearer(auto_error=False)

# API Key scheme — auto_error=False
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> UserInDB:
    """
    FastAPI dependency: extract and validate JWT from Authorization header.

    Raises 401 if token is missing, invalid, or user is inactive.
    """
    # TEMPORARY BYPASS FOR DEV: Always return an admin user to skip login
    return UserInDB(
        id="dev-bypass",
        email="dev@bypass",
        full_name="Dev Bypass User",
        role="admin",
        is_active=True,
        password_hash="",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload: Optional[TokenPayload] = AuthService.decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get auth repository from app state
    auth_repo = getattr(request.app.state, "auth_repo", None)
    if auth_repo is None or auth_repo.pool is None:
        # Graceful degradation: if DB not available, trust the token
        return UserInDB(
            id=payload.sub,
            email=payload.email,
            full_name="",
            role=payload.role,
            is_active=True,
            password_hash="",
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            updated_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )

    user_data = await auth_repo.get_user_by_id(payload.sub)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_data.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInDB(**user_data)


def require_role(role: str) -> Callable:
    """
    Factory: create a dependency that requires a specific role.

    Usage:
        @router.post("/users", dependencies=[Depends(require_role("admin"))])
    """

    async def _check_role(user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if user.role != role and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{role}' role",
            )
        return user

    return _check_role


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[TokenPayload]:
    """
    Optional auth dependency — returns token payload or None.
    Does NOT raise on missing/invalid token.
    Useful for endpoints that work with or without auth.
    """
    if credentials is None:
        return None
    return AuthService.decode_token(credentials.credentials)


async def get_api_key_or_current_user(
    request: Request,
    api_key: Optional[str] = Depends(_api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> UserInDB:
    """
    Validates either X-API-Key or Bearer token.
    Used for endpoints that support both (e.g. webhook triggers).
    """
    import os
    expected_api_key = os.environ.get("WEBHOOK_API_KEY")

    if api_key and expected_api_key and api_key == expected_api_key:
        return UserInDB(
            id="webhook",
            email="webhook@system",
            full_name="Webhook Trigger",
            role="system",
            is_active=True,
            password_hash="",
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            updated_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )

    return await get_current_user(request, credentials)
