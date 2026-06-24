"""
Alembic environment configuration for Doc Intelligence.

Reads DATABASE_URL from environment (same source as the application).
Supports both online (connected) and offline (SQL generation) modes.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Add backend/ to path so we can import settings
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

config = context.config
fileConfig(config.config_file_name)


def get_database_url() -> str:
    """Resolve DATABASE_URL from environment or .env file."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Try loading from .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        url = os.environ.get("DATABASE_URL")
    except ImportError:
        pass

    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required for migrations. "
            "Set it in .env or pass directly: DATABASE_URL=postgresql://... alembic upgrade head"
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to database."""
    url = get_database_url()

    # Convert asyncpg URL to psycopg2/sync format for Alembic
    # asyncpg uses: postgresql://user:pass@host/db
    # sqlalchemy sync needs the same (uses psycopg2 by default)
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")

    # Append sslmode=disable for local Docker PostgreSQL
    if "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=disable"

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
