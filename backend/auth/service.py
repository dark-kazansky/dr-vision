"""
Auth service — JWT creation/verification and password hashing.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from auth.models import TokenPayload, UserInDB
from settings import settings

logger = logging.getLogger(__name__)

# Password hashing context
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Stateless authentication service."""

    # Token lifetimes
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    @staticmethod
    def hash_password(plain: str) -> str:
        """Hash a plaintext password with bcrypt."""
        return _pwd_context.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plaintext password against its hash."""
        return _pwd_context.verify(plain, hashed)

    @classmethod
    def create_tokens(cls, user: UserInDB) -> Tuple[str, str, int]:
        """
        Create access + refresh token pair.

        Returns:
            (access_token, refresh_token, expires_in_seconds)
        """
        now = datetime.now(timezone.utc)
        access_exp = now + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_exp = now + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)

        access_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(access_exp.timestamp()),
        }

        refresh_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(refresh_exp.timestamp()),
        }

        secret = settings.jwt_secret_key
        algorithm = settings.jwt_algorithm

        access_token = jwt.encode(access_payload, secret, algorithm=algorithm)
        refresh_token = jwt.encode(refresh_payload, secret, algorithm=algorithm)

        expires_in = cls.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, refresh_token, expires_in

    @staticmethod
    def decode_token(token: str) -> Optional[TokenPayload]:
        """
        Decode and validate a JWT token.

        Returns None if token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return TokenPayload(**payload)
        except JWTError:
            return None

    @staticmethod
    def generate_api_key() -> str:
        """Generate a random API key for webhook authentication."""
        return f"drvision_{uuid.uuid4().hex}"
