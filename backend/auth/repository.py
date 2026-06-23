"""
Auth repository — PostgreSQL storage for users.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import asyncpg

logger = logging.getLogger(__name__)


# =============================================================================
# DDL
# =============================================================================

_CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(32) PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);
"""

_CREATE_USERS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
"""

_CREATE_API_KEYS_TABLE = """
CREATE TABLE IF NOT EXISTS api_keys (
    id              VARCHAR(32) PRIMARY KEY,
    user_id         VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash        TEXT NOT NULL,
    name            VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used       TIMESTAMPTZ
);
"""


class AuthRepository:
    """PostgreSQL repository for user and API key management."""

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self._pool = pool

    def set_pool(self, pool: asyncpg.Pool) -> None:
        """Set the connection pool (called during app lifespan)."""
        self._pool = pool

    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        return self._pool

    async def init_schema(self) -> None:
        """Create auth tables if they don't exist."""
        if not self._pool:
            logger.warning("AuthRepository: no pool, skipping schema init")
            return
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_USERS_TABLE)
            await conn.execute(_CREATE_USERS_INDEX)
            await conn.execute(_CREATE_API_KEYS_TABLE)
        logger.info("AuthRepository: schema initialized")

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email. Returns None if not found."""
        if not self._pool:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1", email
            )
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID. Returns None if not found."""
        if not self._pool:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
            return dict(row) if row else None

    async def create_user(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "user",
    ) -> dict:
        """Create a new user. Raises asyncpg.UniqueViolationError if email exists."""
        if not self._pool:
            raise RuntimeError("Database not connected")
        user_id = uuid.uuid4().hex[:32]
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, full_name, role, password_hash, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id, email, full_name, role, password_hash, now, now,
            )
        return {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "password_hash": password_hash,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
        }

    async def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        password_hash: Optional[str] = None,
    ) -> Optional[dict]:
        """Update user fields. Returns updated user or None if not found."""
        if not self._pool:
            return None

        updates = []
        params = []
        idx = 1

        if full_name is not None:
            updates.append(f"full_name = ${idx}")
            params.append(full_name)
            idx += 1
        if role is not None:
            updates.append(f"role = ${idx}")
            params.append(role)
            idx += 1
        if is_active is not None:
            updates.append(f"is_active = ${idx}")
            params.append(is_active)
            idx += 1
        if password_hash is not None:
            updates.append(f"password_hash = ${idx}")
            params.append(password_hash)
            idx += 1

        if not updates:
            return await self.get_user_by_id(user_id)

        updates.append(f"updated_at = ${idx}")
        params.append(datetime.now(timezone.utc))
        idx += 1

        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx} RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            return dict(row) if row else None

    async def update_last_login(self, user_id: str) -> None:
        """Update last_login timestamp."""
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = $1 WHERE id = $2",
                datetime.now(timezone.utc), user_id,
            )

    async def list_users(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """List all users (admin function)."""
        if not self._pool:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
            return [dict(r) for r in rows]

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user. Returns True if deleted."""
        if not self._pool:
            return False
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM users WHERE id = $1", user_id
            )
            return result == "DELETE 1"

    async def count_users(self) -> int:
        """Count total users."""
        if not self._pool:
            return 0
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM users")
            return row["cnt"] if row else 0
